#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_RUNTIME_DEV_PYTHON="$ROOT_DIR/dist/runtime-dev/python/bin/python"
LEGACY_RUNTIME_DEV_PYTHON="$ROOT_DIR/dist/runtime-dev/bin/python"
RUNTIME_DEV_PYTHON="${RUNTIME_DEV_PYTHON:-$DEFAULT_RUNTIME_DEV_PYTHON}"

DEFAULT_TESTS=(
  "packages/agents/recording-agent-runtime-local/tests/test_service.py"
)

if [ "$#" -gt 0 ]; then
  TEST_TARGETS=("$@")
else
  TEST_TARGETS=("${DEFAULT_TESTS[@]}")
fi

if [ ! -x "$RUNTIME_DEV_PYTHON" ] && [ -x "$LEGACY_RUNTIME_DEV_PYTHON" ]; then
  RUNTIME_DEV_PYTHON="$LEGACY_RUNTIME_DEV_PYTHON"
fi

if [ ! -x "$RUNTIME_DEV_PYTHON" ]; then
  echo "SKIPPED: runtime-dependent tests require runtime-dev Python"
  echo "Missing runtime: $RUNTIME_DEV_PYTHON"
  printf 'Skipped targets:\n'
  for target in "${TEST_TARGETS[@]}"; do
    echo "  - $target"
  done
  exit 0
fi

SRC_DIRS_RAW="$("$RUNTIME_DEV_PYTHON" - <<'PY' "$ROOT_DIR"
from pathlib import Path
import sys

root_dir = Path(sys.argv[1])
src_dirs: list[Path] = [root_dir / "src"]

for child in root_dir.iterdir():
    if not child.is_dir():
        continue
    if (child / "pyproject.toml").is_file():
        src_dir = child / "src"
        if src_dir.is_dir():
            src_dirs.append(src_dir.resolve())

seen: set[Path] = set()
for path in src_dirs:
    resolved = path.resolve()
    if resolved in seen:
        continue
    seen.add(resolved)
    print(resolved)
PY
)"

SRC_DIRS=()
while IFS= read -r line; do
  if [ -n "$line" ]; then
    SRC_DIRS+=("$line")
  fi
done <<EOF
$SRC_DIRS_RAW
EOF

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

echo "Using runtime-dependent Python: $RUNTIME_DEV_PYTHON"
printf 'Running targets:\n'
for target in "${TEST_TARGETS[@]}"; do
  echo "  - $target"
done

PYTHONPATH="$PYTHONPATH_PREFIX" \
  "$RUNTIME_DEV_PYTHON" -m pytest --import-mode=importlib "${TEST_TARGETS[@]}"
