#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_TARGET_ROOT="${SOURCE_ROOT}/public/munk-ai"

TARGET_ROOT="${DEFAULT_TARGET_ROOT}"
DRY_RUN=0

REQUIRED_FILES=(
  ".gitignore"
  "LICENSE.txt"
  "README.md"
)

SYNC_DIRS=(
  "apps"
  "assets"
  "config"
  "packages"
  "scripts"
  "sidecars"
  "src"
)

RSYNC_EXCLUDES=(
  "--exclude=.DS_Store"
  "--exclude=.idea/"
  "--exclude=.vscode/"
  "--exclude=.trae/"
  "--exclude=__pycache__/"
  "--exclude=*.pyc"
  "--exclude=*.pyo"
  "--exclude=*.egg-info/"
  "--exclude=.eggs/"
  "--exclude=.pytest_cache/"
  "--exclude=.mypy_cache/"
  "--exclude=.ruff_cache/"
  "--exclude=.coverage"
  "--exclude=.venv/"
  "--exclude=venv/"
  "--exclude=node_modules/"
  "--exclude=.pnpm-store/"
  "--exclude=.cache/"
  "--exclude=build/"
  "--exclude=dist/"
  "--exclude=tmp/"
  "--exclude=.tmp/"
  "--exclude=.dbg/"
  "--exclude=development-log/"
  "--exclude=public/"
  "--exclude=.munk/"
  "--exclude=.review-runtime-local/"
  "--exclude=internal/"
  "--exclude=runs/"
  "--exclude=operations.sqlite3"
  "--exclude=*.sqlite3-wal"
  "--exclude=*.sqlite3-shm"
  "--exclude=models/"
  "--exclude=logo/"
)

print_help() {
  cat <<'EOF'
Sync the public repository subset from the private workspace.

Usage:
  ./scripts/sync_public_repo.sh [--target PATH] [--dry-run]

Options:
  --target PATH  Override the target repository path.
  --dry-run      Show the rsync plan without writing changes.
  --help         Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --target" >&2
        exit 1
      fi
      TARGET_ROOT="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help)
      print_help
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      print_help >&2
      exit 1
      ;;
  esac
done

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required but was not found in PATH" >&2
  exit 1
fi

TARGET_ROOT="$(cd -- "$(dirname -- "${TARGET_ROOT}")" && pwd)/$(basename -- "${TARGET_ROOT}")"

if [[ "${TARGET_ROOT}" == "${SOURCE_ROOT}" ]]; then
  echo "Target path must not be the same as the source repository root" >&2
  exit 1
fi

mkdir -p "${TARGET_ROOT}"

RSYNC_COMMON=(
  rsync
  -a
  --human-readable
  --itemize-changes
)

if [[ ${DRY_RUN} -eq 1 ]]; then
  RSYNC_COMMON+=("--dry-run")
fi

sync_file() {
  local relative_path="$1"
  local source_path="${SOURCE_ROOT}/${relative_path}"
  local target_path="${TARGET_ROOT}/${relative_path}"

  if [[ ! -f "${source_path}" ]]; then
    echo "Missing required file: ${relative_path}" >&2
    exit 1
  fi

  mkdir -p "$(dirname -- "${target_path}")"
  echo "Sync file: ${relative_path}"
  "${RSYNC_COMMON[@]}" "${source_path}" "${target_path}"
}

sync_dir() {
  local relative_path="$1"
  local source_path="${SOURCE_ROOT}/${relative_path}"
  local target_path="${TARGET_ROOT}/${relative_path}"

  if [[ ! -d "${source_path}" ]]; then
    echo "Missing required directory: ${relative_path}" >&2
    exit 1
  fi

  mkdir -p "${target_path}"
  echo "Sync dir: ${relative_path}/"
  "${RSYNC_COMMON[@]}" --delete "${RSYNC_EXCLUDES[@]}" "${source_path}/" "${target_path}/"
}

sync_dir_if_present() {
  local relative_path="$1"
  local source_path="${SOURCE_ROOT}/${relative_path}"

  if [[ ! -d "${source_path}" ]]; then
    echo "Skip dir: ${relative_path}/ (not found in source)"
    return
  fi

  sync_dir "${relative_path}"
}

echo "Source: ${SOURCE_ROOT}"
echo "Target: ${TARGET_ROOT}"
if [[ ${DRY_RUN} -eq 1 ]]; then
  echo "Mode: dry-run"
fi

for file_path in "${REQUIRED_FILES[@]}"; do
  sync_file "${file_path}"
done

for dir_path in "${SYNC_DIRS[@]}"; do
  sync_dir_if_present "${dir_path}"
done

echo "Public repository sync completed."
