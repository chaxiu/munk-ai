#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${RUNTIME_ROOT:-$ROOT_DIR/dist/runtime-dev}"

python3 "$ROOT_DIR/scripts/update_uv_locks.py"
python3 "$ROOT_DIR/scripts/bootstrap_standalone_dev.py" --runtime-root "$RUNTIME_ROOT"

echo "已完成 review 开发环境安装"
echo "runtime_root: $RUNTIME_ROOT"
echo "运行时以当前已安装 review runtime 为准"
