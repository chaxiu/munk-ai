#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
PYTHON_BIN="${PYTHON_BIN:-$DEFAULT_PYTHON_BIN}"
BUILD_CONFIG="${BUILD_CONFIG:-$ROOT_DIR/config/build/build.yaml}"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="python3"
fi

TEST_DIRS=()
SRC_DIRS=()
while IFS=$'\t' read -r kind path; do
  case "$kind" in
    TEST)
      TEST_DIRS+=("$path")
      ;;
    SRC)
      SRC_DIRS+=("$path")
      ;;
  esac
done < <("$PYTHON_BIN" - <<'PY' "$ROOT_DIR" "$BUILD_CONFIG"
from pathlib import Path
import sys

import yaml

root_dir = Path(sys.argv[1])
build_config = Path(sys.argv[2])

test_dirs: list[Path] = [root_dir / "tests"]
src_dirs: list[Path] = [root_dir / "src"]


def add_workspace_repo(repo_path: Path) -> None:
    tests_dir = repo_path / "tests"
    src_dir = repo_path / "src"
    if tests_dir.is_dir():
        test_dirs.append(tests_dir)
    if src_dir.is_dir():
        src_dirs.append(src_dir)


for child in root_dir.iterdir():
    if not child.is_dir():
        continue
    if (child / "pyproject.toml").is_file():
        add_workspace_repo(child)

if build_config.exists():
    raw = yaml.safe_load(build_config.read_text(encoding="utf-8")) or {}
    perception = raw.get("perception") or {}
    for key in ("api_path", "provider_path"):
        value = perception.get(key)
        if not value:
            continue
        repo_path = (root_dir / value).expanduser().resolve()
        add_workspace_repo(repo_path)

def unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(resolved)
    return result


for path in unique(test_dirs):
    print("TEST", path, sep="\t")
for path in unique(src_dirs):
    print("SRC", path, sep="\t")
PY
)

echo "发现以下测试目录:"
for dir in "${TEST_DIRS[@]}"; do
  echo "  - $dir"
done

PYTHONPATH_PREFIX=""
for dir in "${SRC_DIRS[@]}"; do
  if [ -z "$PYTHONPATH_PREFIX" ]; then
    PYTHONPATH_PREFIX="$dir"
  else
    PYTHONPATH_PREFIX="$PYTHONPATH_PREFIX:$dir"
  fi
done

if [ -n "${PYTHONPATH:-}" ]; then
  PYTHONPATH_PREFIX="$PYTHONPATH_PREFIX:$PYTHONPATH"
fi

PYTHONPATH="$PYTHONPATH_PREFIX" \
  "$PYTHON_BIN" -m pytest --import-mode=importlib "${TEST_DIRS[@]}" "$@"
