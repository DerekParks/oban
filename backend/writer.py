"""Write tasks to Obsidian Kanban markdown files."""

import re
from pathlib import Path


def add_task_to_column(filepath: Path, column_index: int, task_text: str):
    """Add an unchecked task to the specified column of a kanban file.

    Inserts the task at the end of the column's task list, before
    the next column header or the settings block.
    """
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Find all column header positions
    column_positions: list[int] = []
    for i, line in enumerate(lines):
        if line.rstrip().startswith("## "):
            column_positions.append(i)

    if column_index >= len(column_positions):
        raise ValueError(f"Column index {column_index} out of range (board has {len(column_positions)} columns)")

    # Find the insertion point: last task line in the column, or right after the header
    col_start = column_positions[column_index]
    if column_index + 1 < len(column_positions):
        col_end = column_positions[column_index + 1]
    else:
        # Last column — find the settings block or end of file
        col_end = len(lines)
        for i in range(col_start + 1, len(lines)):
            if lines[i].rstrip().startswith("%% kanban:settings"):
                col_end = i
                break

    # Find the last task line in the column range
    last_task_line = col_start
    for i in range(col_start + 1, col_end):
        stripped = lines[i].rstrip()
        if stripped.startswith("- ["):
            last_task_line = i

    # Insert after the last task, or after the header if no tasks
    insert_at = last_task_line + 1
    new_line = f"- [ ] {task_text}\n"
    lines.insert(insert_at, new_line)

    filepath.write_text("".join(lines), encoding="utf-8")


def remove_task_from_column(filepath: Path, column_index: int, task_index: int):
    """Remove a task by its index within a column."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    column_positions: list[int] = []
    for i, line in enumerate(lines):
        if line.rstrip().startswith("## "):
            column_positions.append(i)

    if column_index >= len(column_positions):
        raise ValueError(f"Column index {column_index} out of range")

    col_start = column_positions[column_index]
    if column_index + 1 < len(column_positions):
        col_end = column_positions[column_index + 1]
    else:
        col_end = len(lines)
        for i in range(col_start + 1, len(lines)):
            if lines[i].rstrip().startswith("%% kanban:settings"):
                col_end = i
                break

    # Find the Nth task line in the column
    task_count = 0
    for i in range(col_start + 1, col_end):
        if lines[i].rstrip().startswith("- ["):
            if task_count == task_index:
                del lines[i]
                filepath.write_text("".join(lines), encoding="utf-8")
                return
            task_count += 1

    raise ValueError(f"Task index {task_index} not found in column")


def pop_task_from_column(filepath: Path, column_index: int, task_index: int) -> str:
    """Remove a task and return its raw markdown line."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    column_positions: list[int] = []
    for i, line in enumerate(lines):
        if line.rstrip().startswith("## "):
            column_positions.append(i)

    if column_index >= len(column_positions):
        raise ValueError(f"Column index {column_index} out of range")

    col_start = column_positions[column_index]
    if column_index + 1 < len(column_positions):
        col_end = column_positions[column_index + 1]
    else:
        col_end = len(lines)
        for i in range(col_start + 1, len(lines)):
            if lines[i].rstrip().startswith("%% kanban:settings"):
                col_end = i
                break

    task_count = 0
    for i in range(col_start + 1, col_end):
        if lines[i].rstrip().startswith("- ["):
            if task_count == task_index:
                raw_line = lines[i].rstrip()
                del lines[i]
                filepath.write_text("".join(lines), encoding="utf-8")
                return raw_line
            task_count += 1

    raise ValueError(f"Task index {task_index} not found in column")


def insert_raw_task(filepath: Path, column_index: int, task_index: int, raw_line: str):
    """Insert a raw task line at a specific position within a column."""
    text = filepath.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    column_positions: list[int] = []
    for i, line in enumerate(lines):
        if line.rstrip().startswith("## "):
            column_positions.append(i)

    if column_index >= len(column_positions):
        raise ValueError(f"Column index {column_index} out of range")

    col_start = column_positions[column_index]
    if column_index + 1 < len(column_positions):
        col_end = column_positions[column_index + 1]
    else:
        col_end = len(lines)
        for i in range(col_start + 1, len(lines)):
            if lines[i].rstrip().startswith("%% kanban:settings"):
                col_end = i
                break

    # Find the position to insert at
    task_count = 0
    insert_at = col_start + 1  # default: right after header
    for i in range(col_start + 1, col_end):
        if lines[i].rstrip().startswith("- ["):
            if task_count == task_index:
                insert_at = i
                break
            task_count += 1
            insert_at = i + 1  # after the last task seen

    lines.insert(insert_at, raw_line + "\n")
    filepath.write_text("".join(lines), encoding="utf-8")
