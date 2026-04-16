"""Oban — Obsidian Kanban web dashboard backend."""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
from watchdog.observers import Observer

from config import KANBAN_DIR, OBSIDIAN_VAULT, BOARD_COLUMNS, DEFAULT_DASHBOARD_COLUMN, PINNED_BOARD, STRIP_SUFFIX, WIP_LIMIT, dashboard_column_for
from parser import Board, parse_all_boards, parse_board
from writer import add_task_to_column, remove_task_from_column, pop_task_from_column, insert_raw_task


# --- State ---

_boards: dict[str, Board] = {}
_board_files: dict[str, Path] = {}  # board name -> file path
_connected_clients: set[WebSocket] = set()
_observer: Observer | None = None
_last_api_write: float = 0  # monotonic timestamp of last API file write


class AddTaskRequest(BaseModel):
    board: str
    text: str
    column_index: int | None = None


class DeleteTaskRequest(BaseModel):
    board: str
    column_index: int
    task_index: int


class CompleteTaskRequest(BaseModel):
    board: str
    column_index: int
    task_index: int


class MoveTaskRequest(BaseModel):
    from_board: str
    from_column: int
    from_index: int
    to_board: str
    to_column: int
    to_index: int


def _boards_payload() -> str:
    """Serialize current board state to JSON."""
    return json.dumps({"boards": [asdict(b) for b in _boards.values()]})


def _dashboard_payload() -> str:
    """Serialize dashboard tasks per board."""
    result = []
    for b in _boards.values():
        col_idx = dashboard_column_for(b.name)
        col = b.get_dashboard_column(col_idx)
        result.append({
            "name": b.name,
            "column_name": col.name if col else None,
            "column_index": col_idx,
            "tasks": [asdict(t) for t in col.tasks] if col else [],
        })
    return json.dumps({"boards": result})


async def _broadcast(message: str):
    """Send message to all connected WebSocket clients."""
    disconnected = set()
    for ws in _connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        _connected_clients.discard(ws)


# --- File watcher ---

class KanbanFileHandler(FileSystemEventHandler):
    """Watches for .md file changes and triggers board refresh."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._last_event_time: float = 0
        self._debounce_seconds = 0.5

    def _handle(self, event):
        global _last_api_write
        path = Path(event.src_path)
        if path.suffix != ".md":
            return

        # Debounce: skip if last event was very recent
        now = time.monotonic()
        if now - self._last_event_time < self._debounce_seconds:
            return
        self._last_event_time = now

        # Skip if an API handler recently wrote files — it handles
        # its own re-parse and broadcast, so ours would be redundant
        # and could race (stale data overwriting the correct broadcast).
        if now - _last_api_write < 1.0:
            return

        if isinstance(event, FileDeletedEvent):
            board_name = path.stem
            if STRIP_SUFFIX and board_name.endswith(STRIP_SUFFIX):
                board_name = board_name[: -len(STRIP_SUFFIX)]
            _boards.pop(board_name, None)
            _board_files.pop(board_name, None)
        else:
            board = parse_board(path)
            if board:
                _boards[board.name] = board
                _board_files[board.name] = path

        asyncio.run_coroutine_threadsafe(
            _broadcast(_dashboard_payload()), self._loop
        )

    def on_modified(self, event):
        self._handle(event)

    def on_created(self, event):
        self._handle(event)

    def on_deleted(self, event):
        self._handle(event)


# --- App lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _observer

    # Load all boards on startup
    for filepath in sorted(KANBAN_DIR.glob("*.md")):
        board = parse_board(filepath)
        if board:
            _boards[board.name] = board
            _board_files[board.name] = filepath

    # Start file watcher
    loop = asyncio.get_running_loop()
    handler = KanbanFileHandler(loop)
    _observer = Observer()
    _observer.schedule(handler, str(KANBAN_DIR), recursive=False)
    _observer.start()

    yield

    # Shutdown
    if _observer:
        _observer.stop()
        _observer.join()


# --- FastAPI app ---

app = FastAPI(title="Oban", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/boards")
def get_boards_dashboard():
    """Return dashboard tasks for all boards."""
    result = []
    for b in _boards.values():
        col_idx = dashboard_column_for(b.name)
        col = b.get_dashboard_column(col_idx)
        result.append({
            "name": b.name,
            "column_name": col.name if col else None,
            "column_index": col_idx,
            "tasks": [asdict(t) for t in col.tasks] if col else [],
        })
    return {"boards": result}


@app.get("/api/boards/{name}")
def get_board(name: str):
    """Return full board detail (all columns)."""
    board = _boards.get(name)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return asdict(board)


@app.get("/api/config")
def get_config():
    """Return client-facing config."""
    return {
        "obsidian_vault": OBSIDIAN_VAULT,
        "default_column": DEFAULT_DASHBOARD_COLUMN,
        "board_columns": BOARD_COLUMNS,
        "pinned_board": PINNED_BOARD,
        "wip_limit": WIP_LIMIT,
    }


@app.get("/api/board-names")
def get_board_names():
    """Return list of all board names."""
    return {"names": sorted(_boards.keys())}


@app.post("/api/tasks")
async def add_task(req: AddTaskRequest):
    """Add a task to the in-progress column of a board."""
    board = _boards.get(req.board)
    filepath = _board_files.get(req.board)
    if not board or not filepath:
        raise HTTPException(status_code=404, detail="Board not found")

    global _last_api_write
    col_idx = req.column_index if req.column_index is not None else dashboard_column_for(req.board)
    _last_api_write = time.monotonic()
    add_task_to_column(filepath, col_idx, req.text)

    # Re-parse to update in-memory state
    updated = parse_board(filepath)
    if updated:
        _boards[updated.name] = updated

    # Broadcast updated state to all WebSocket clients
    await _broadcast(_dashboard_payload())

    return {"ok": True}


@app.post("/api/tasks/complete")
async def complete_task(req: CompleteTaskRequest):
    """Move a task to the last (done) column of its board."""
    board = _boards.get(req.board)
    filepath = _board_files.get(req.board)
    if not board or not filepath:
        raise HTTPException(status_code=404, detail="Board not found")
    global _last_api_write
    _last_api_write = time.monotonic()

    done_column = len(board.columns) - 1

    if len(board.columns) < 2 or req.column_index >= done_column:
        # Already in the last column or no done column — just delete the task
        remove_task_from_column(filepath, req.column_index, req.task_index)
    else:
        raw_line = pop_task_from_column(filepath, req.column_index, req.task_index)
        insert_raw_task(filepath, done_column, 0, raw_line)

    updated = parse_board(filepath)
    if updated:
        _boards[updated.name] = updated

    await _broadcast(_dashboard_payload())
    return {"ok": True}


@app.post("/api/tasks/move")
async def move_task(req: MoveTaskRequest):
    """Move a task between boards/columns."""
    src_filepath = _board_files.get(req.from_board)
    dst_filepath = _board_files.get(req.to_board)
    if not src_filepath or not dst_filepath:
        raise HTTPException(status_code=404, detail="Board not found")

    global _last_api_write
    _last_api_write = time.monotonic()

    # Pop from source
    raw_line = pop_task_from_column(src_filepath, req.from_column, req.from_index)

    # Insert into destination
    insert_raw_task(dst_filepath, req.to_column, req.to_index, raw_line)

    # Re-parse both boards
    for name, fpath in [(req.from_board, src_filepath), (req.to_board, dst_filepath)]:
        updated = parse_board(fpath)
        if updated:
            _boards[updated.name] = updated

    await _broadcast(_dashboard_payload())
    return {"ok": True}


@app.delete("/api/tasks")
async def delete_task(req: DeleteTaskRequest):
    """Remove a task from a board column."""
    board = _boards.get(req.board)
    filepath = _board_files.get(req.board)
    if not board or not filepath:
        raise HTTPException(status_code=404, detail="Board not found")

    global _last_api_write
    _last_api_write = time.monotonic()
    remove_task_from_column(filepath, req.column_index, req.task_index)

    updated = parse_board(filepath)
    if updated:
        _boards[updated.name] = updated

    await _broadcast(_dashboard_payload())

    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _connected_clients.add(ws)
    try:
        # Send initial state
        await ws.send_text(_dashboard_payload())
        # Keep alive — wait for client to disconnect
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _connected_clients.discard(ws)


# Serve frontend static files in production (must be after API routes)
_static_dir = Path(__file__).parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
