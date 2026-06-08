from __future__ import annotations

import array
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import sqlite3

try:  # pragma: no cover - import depends on environment
    import sqlite_vec as _sqlite_vec  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - import depends on environment
    _sqlite_vec = None


def sqlite_vec_available() -> bool:
    return _sqlite_vec is not None


def load_sqlite_vec(connection: "sqlite3.Connection") -> None:
    if _sqlite_vec is None:
        raise RuntimeError(
            "sqlite-vec is not installed; install project dependencies with review extras before building or querying the review knowledge database"
        )
    _sqlite_vec.load(connection)


def serialize_float32(vector: Any) -> bytes:
    if _sqlite_vec is not None:
        return cast(bytes, _sqlite_vec.serialize_float32(vector))
    return cast(bytes, array.array("f", vector).tobytes())
