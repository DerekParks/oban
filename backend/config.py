import json
import os
from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")

VAULT_DIR = Path(os.environ.get("OBAN_VAULT_DIR", "."))
KANBAN_DIR = Path(os.environ.get("OBAN_KANBAN_DIR", str(VAULT_DIR / "kanbans")))
OBSIDIAN_VAULT = os.environ.get("OBAN_OBSIDIAN_VAULT", "")
DEFAULT_DASHBOARD_COLUMN = int(os.environ.get("OBAN_DEFAULT_COLUMN", "1"))
PINNED_BOARD = os.environ.get("OBAN_PINNED_BOARD", "")
STRIP_SUFFIX = os.environ.get("OBAN_STRIP_SUFFIX", " Kanban")
WIP_LIMIT = int(os.environ.get("OBAN_WIP_LIMIT", "15"))

# Per-board column overrides: { "Board Name": column_index }
# Loaded from oban.boards.json if it exists
_boards_config_path = _root / "oban.boards.json"
BOARD_COLUMNS: dict[str, int] = {}
if _boards_config_path.is_file():
    BOARD_COLUMNS = json.loads(_boards_config_path.read_text(encoding="utf-8"))


def dashboard_column_for(board_name: str) -> int:
    """Return the dashboard column index for a given board."""
    return BOARD_COLUMNS.get(board_name, DEFAULT_DASHBOARD_COLUMN)
