"""Parser for Obsidian Kanban plugin markdown files."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from config import STRIP_SUFFIX


@dataclass
class Task:
    text: str
    completed: bool


@dataclass
class Column:
    name: str
    tasks: list[Task] = field(default_factory=list)


@dataclass
class Board:
    name: str
    columns: list[Column] = field(default_factory=list)

    def get_dashboard_column(self, col_index: int) -> Column | None:
        """Return the column at the given index, or None."""
        if col_index < len(self.columns):
            return self.columns[col_index]
        return None


_TASK_RE = re.compile(r"^- \[([ xX])\] (.+)$")


def parse_board(filepath: Path) -> Board | None:
    """Parse an Obsidian Kanban markdown file into a Board."""
    text = filepath.read_text(encoding="utf-8")

    # Strip kanban settings block at the end
    text = re.sub(r"\n*%% kanban:settings.*?%%\s*$", "", text, flags=re.DOTALL)

    # Strip YAML frontmatter
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)

    board_name = filepath.stem
    # Remove configured suffix if present for cleaner display
    if STRIP_SUFFIX and board_name.endswith(STRIP_SUFFIX):
        board_name = board_name[: -len(STRIP_SUFFIX)]

    columns: list[Column] = []
    current_column: Column | None = None

    for line in text.splitlines():
        line = line.rstrip()

        # Column header
        if line.startswith("## "):
            current_column = Column(name=line[3:].strip())
            columns.append(current_column)
            continue

        # Skip bold section headers like **Complete**
        if line.startswith("**") and line.endswith("**"):
            continue

        # Task line
        if current_column is not None:
            m = _TASK_RE.match(line)
            if m:
                completed = m.group(1).lower() == "x"
                task_text = m.group(2).strip()
                current_column.tasks.append(Task(text=task_text, completed=completed))

    if not columns:
        return None

    return Board(name=board_name, columns=columns)


def parse_all_boards(kanban_dir: Path) -> list[Board]:
    """Parse all Kanban markdown files in a directory."""
    boards = []
    for filepath in sorted(kanban_dir.glob("*.md")):
        board = parse_board(filepath)
        if board is not None:
            boards.append(board)
    return boards
