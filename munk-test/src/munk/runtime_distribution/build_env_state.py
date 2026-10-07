from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import cast


def default_state_path(*, project_root: Path, kind: str, runtime_root: Path) -> Path:
    return project_root / "dist" / "runtime-build" / f"{kind}-{runtime_root.name}-state.json"


def load_state(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    payload_dict = cast(dict[object, object], payload)
    return {str(key): value for key, value in payload_dict.items()}


def write_state(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fingerprint_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    seen: set[Path] = set()
    for path in sorted({path.resolve() for path in paths}):
        if path in seen:
            continue
        seen.add(path)
        if not path.exists():
            digest.update(f"missing:{path}".encode("utf-8"))
            continue
        if path.is_file():
            if should_ignore_fingerprint_path(path):
                continue
            update_digest_for_file(digest, path)
            continue
        digest.update(f"dir:{path}".encode("utf-8"))
        for child in sorted(path.rglob("*")):
            if should_ignore_fingerprint_path(child):
                continue
            if child.is_dir():
                digest.update(f"subdir:{child.relative_to(path)}".encode("utf-8"))
                continue
            update_digest_for_file(digest, child, relative_to=path)
    return digest.hexdigest()


def run_command(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, cwd=cwd, env=env)


def should_ignore_fingerprint_path(path: Path) -> bool:
    ignored_names = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv", ".DS_Store"}
    if any(part in ignored_names for part in path.parts):
        return True
    if any(part.endswith(".egg-info") for part in path.parts):
        return True
    for index, part in enumerate(path.parts[:-1]):
        if part == "review_knowledge" and path.parts[index + 1] == "build":
            return True
    return path.suffix in {".pyc", ".pyo"}


def update_digest_for_file(
    digest: hashlib._Hash,
    path: Path,
    *,
    relative_to: Path | None = None,
) -> None:
    label = str(path.relative_to(relative_to)) if relative_to is not None else str(path)
    digest.update(f"file:{label}:".encode("utf-8"))
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
