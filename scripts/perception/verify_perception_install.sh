#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${RUNTIME_ROOT:-$ROOT_DIR/dist/runtime-release}"
SMOKE_IMAGE="$ROOT_DIR/runs/run_20260502_210529_272353_94cdb091/screenshots/raw/step_0000.png"
SMOKE_OUTPUT="${SMOKE_OUTPUT:-/tmp/munk_perception_release_annotated.png}"

python3 "$ROOT_DIR/scripts/update_uv_locks.py"
python3 "$ROOT_DIR/scripts/assemble_standalone_runtime.py" --runtime-root "$RUNTIME_ROOT" --force
"$RUNTIME_ROOT/bin/munk" doctor
"$RUNTIME_ROOT/bin/munk" annotate "$SMOKE_IMAGE" --output "$SMOKE_OUTPUT"

echo "已完成 perception 安装验证: $RUNTIME_ROOT"
