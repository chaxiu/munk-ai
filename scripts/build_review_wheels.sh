#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT_DIR/scripts/update_uv_locks.py"
uv run --with build>=1.2.2 --project "$ROOT_DIR/packages/agents/review-agent-api" python -m build "$ROOT_DIR/packages/agents/review-agent-api"
uv run --with build>=1.2.2 --project "$ROOT_DIR/packages/agents/review-agent-runtime-local" python -m build "$ROOT_DIR/packages/agents/review-agent-runtime-local"
uv run --with build>=1.2.2 --project "$ROOT_DIR" python -m build "$ROOT_DIR"

echo "已完成 review 相关 wheel 构建"
