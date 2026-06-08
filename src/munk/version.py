from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

PROJECT_VERSION_PATTERN = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$')


def resolve_munk_version() -> str:
    try:
        return package_version("munk")
    except PackageNotFoundError:
        return _version_from_repo_pyproject() or "0.1.0"


def _version_from_repo_pyproject() -> str | None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject_path.exists():
        return None
    in_project_section = False
    for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("["):
            in_project_section = line == "[project]"
            continue
        if not in_project_section:
            continue
        match = PROJECT_VERSION_PATTERN.match(raw_line)
        if match is not None:
            return match.group(1)
    return None
