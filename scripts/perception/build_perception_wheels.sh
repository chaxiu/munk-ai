#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT_DIR/scripts/update_uv_locks.py"

pushd "$ROOT_DIR/packages/shared/perception-api" >/dev/null
uv run --with 'build>=1.2.2' python -m build --wheel --outdir "$ROOT_DIR/packages/shared/perception-api/dist" .
popd >/dev/null

pushd "$ROOT_DIR/packages/shared/perception-sdk-full" >/dev/null
uv run --project "$ROOT_DIR/packages/shared/perception-sdk-full" python "$ROOT_DIR/packages/shared/perception-sdk-full/build_helpers.py" prepare-icon-model
uv run --with 'build>=1.2.2' python -m build --wheel --outdir "$ROOT_DIR/packages/shared/perception-sdk-full/dist" .
popd >/dev/null

pushd "$ROOT_DIR" >/dev/null
uv run --with 'build>=1.2.2' python -m build --wheel --outdir "$ROOT_DIR/dist" .
popd >/dev/null

echo "已完成 perception 相关 wheel 构建"
