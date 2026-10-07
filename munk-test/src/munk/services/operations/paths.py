from __future__ import annotations

from pathlib import Path

from munk.user_data import operations_home


def operations_root() -> Path:
    path = operations_home()
    path.mkdir(parents=True, exist_ok=True)
    return path


def operations_db_path() -> Path:
    db_path = operations_home() / "operations.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def operation_dir(operation_id: str) -> Path:
    path = operations_root() / "items" / operation_id
    path.mkdir(parents=True, exist_ok=True)
    return path
