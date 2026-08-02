#!/usr/bin/env bash
# Sync the public open-source subset into public/munk-ai (or --target).
#
# Filter layers (rsync first-match wins):
#   1) Protect filters  — destination-owned paths (e.g. public .github/)
#   2) Policy denylist  — private-only paths (open-source boundary)
#   3) .gitignore       — local noise / large resources (single source of truth)
#   4) Allowlist        — root build manifests + public source trees
#   5) exclude *        — drop every other top-level path (cloud/, dawnchat/, …)
#
# Default uses --delete only (destination .git is preserved because it is
# excluded). Optional --delete-excluded temporarily moves destination .git
# aside, then restores it, so leaked noise can be cleaned safely.
# Public-repo-owned `.github/` is always protected (even with --delete-excluded).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_TARGET_ROOT="${SOURCE_ROOT}/public/munk-ai"
GITIGNORE_PATH="${SOURCE_ROOT}/.gitignore"

TARGET_ROOT="${DEFAULT_TARGET_ROOT}"
DRY_RUN=0
DELETE_EXCLUDED=0

REQUIRED_FILES=(
  ".gitignore"
  ".pre-commit-config.yaml"
  "CONTRIBUTING.md"
  "LICENSE.txt"
  "README.md"
  "package.json"
  "pnpm-lock.yaml"
  "pnpm-workspace.yaml"
  "pyproject.toml"
  "tsconfig.base.json"
  "uv.lock"
)

REQUIRED_DIRS=(
  "apps"
  "assets"
  "packages"
  "scripts"
  "sidecars"
  "src"
)

# Optional trees: sync when present; missing is not an error.
OPTIONAL_DIRS=(
  "config"
  "examples"
)

# Destination-owned paths that must survive sync (including --delete-excluded).
# Release CI lives only on the public repo; private sync must never overwrite it.
PUBLIC_OWNED_PROTECT=(
  "--filter=P /.github/"
  "--filter=P /.github/***"
)

# Open-source policy denylist (Layer B). Paths are relative to SOURCE_ROOT.
# Top-level private trees such as cloud/ are also dropped by the final --exclude=*;
# keep explicit entries so the boundary stays visible.
POLICY_EXCLUDES=(
  "--exclude=/cloud/"
  "--exclude=/.github/"
  "--exclude=/scripts/generate_loop_local_api_openapi.py"
)

print_help() {
  cat <<'EOF'
Sync the public repository subset from the private workspace.

Usage:
  ./scripts/sync_public_repo.sh [--target PATH] [--dry-run] [--delete-excluded]

Options:
  --target PATH        Override the target repository path.
  --dry-run            Show the rsync plan without writing changes.
  --delete-excluded    Also delete destination paths matching exclude rules
                       (safe for .git: it is moved aside and restored;
                       public .github/ is always protected).
  --help               Show this help message.

Filter model:
  protect (.github/)  ->  policy denylist  ->  .gitignore  ->  public allowlist  ->  exclude *

Note:
  Destination .github/ is owned by the public repository (Release CI).
  Sync never copies or deletes it.
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
    --delete-excluded)
      DELETE_EXCLUDED=1
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

if [[ ! -f "${GITIGNORE_PATH}" ]]; then
  echo "Missing .gitignore at ${GITIGNORE_PATH}" >&2
  exit 1
fi

if [[ "${TARGET_ROOT}" != /* ]]; then
  TARGET_ROOT="${SOURCE_ROOT}/${TARGET_ROOT}"
fi
TARGET_ROOT="$(cd -- "$(dirname -- "${TARGET_ROOT}")" && pwd)/$(basename -- "${TARGET_ROOT}")"

if [[ "${TARGET_ROOT}" == "${SOURCE_ROOT}" ]]; then
  echo "Target path must not be the same as the source repository root" >&2
  exit 1
fi

for file_path in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "${SOURCE_ROOT}/${file_path}" ]]; then
    echo "Missing required file: ${file_path}" >&2
    exit 1
  fi
done

for dir_path in "${REQUIRED_DIRS[@]}"; do
  if [[ ! -d "${SOURCE_ROOT}/${dir_path}" ]]; then
    echo "Missing required directory: ${dir_path}" >&2
    exit 1
  fi
done

mkdir -p "${TARGET_ROOT}"

RSYNC_COMMON=(
  rsync
  -a
  --human-readable
  --itemize-changes
  --delete
  --prune-empty-dirs
)

if [[ ${DELETE_EXCLUDED} -eq 1 ]]; then
  RSYNC_COMMON+=("--delete-excluded")
fi

if [[ ${DRY_RUN} -eq 1 ]]; then
  RSYNC_COMMON+=("--dry-run")
fi

RSYNC_FILTERS=(
  "${PUBLIC_OWNED_PROTECT[@]}"
  "${POLICY_EXCLUDES[@]}"
  "--exclude-from=${GITIGNORE_PATH}"
)

for file_path in "${REQUIRED_FILES[@]}"; do
  RSYNC_FILTERS+=("--include=/${file_path}")
done

for dir_path in "${REQUIRED_DIRS[@]}" "${OPTIONAL_DIRS[@]}"; do
  RSYNC_FILTERS+=("--include=/${dir_path}/")
  RSYNC_FILTERS+=("--include=/${dir_path}/***")
done

# Drop every other top-level path (cloud/, dawnchat/, munk-auto/, docs/, …).
RSYNC_FILTERS+=("--exclude=*")

echo "Source: ${SOURCE_ROOT}"
echo "Target: ${TARGET_ROOT}"
echo "Noise filter: ${GITIGNORE_PATH}"
if [[ ${DRY_RUN} -eq 1 ]]; then
  echo "Mode: dry-run"
fi
if [[ ${DELETE_EXCLUDED} -eq 1 ]]; then
  echo "Delete excluded destination paths: yes"
else
  echo "Delete excluded destination paths: no"
fi

GIT_SIDE_DIR=""
restore_target_git() {
  if [[ -n "${GIT_SIDE_DIR}" && -d "${GIT_SIDE_DIR}/.git" ]]; then
    if [[ -e "${TARGET_ROOT}/.git" ]]; then
      echo "Refusing to restore .git over an existing ${TARGET_ROOT}/.git" >&2
      exit 1
    fi
    mv -- "${GIT_SIDE_DIR}/.git" "${TARGET_ROOT}/.git"
    rmdir -- "${GIT_SIDE_DIR}" 2>/dev/null || rm -rf -- "${GIT_SIDE_DIR}"
    GIT_SIDE_DIR=""
  fi
}
trap restore_target_git EXIT

if [[ ${DELETE_EXCLUDED} -eq 1 && ${DRY_RUN} -eq 0 && -d "${TARGET_ROOT}/.git" ]]; then
  GIT_SIDE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/munk-public-git.XXXXXX")"
  echo "Parking destination .git at ${GIT_SIDE_DIR}/.git"
  mv -- "${TARGET_ROOT}/.git" "${GIT_SIDE_DIR}/.git"
fi

echo "Sync public allowlist (rooted at repository root)"
"${RSYNC_COMMON[@]}" "${RSYNC_FILTERS[@]}" "${SOURCE_ROOT}/" "${TARGET_ROOT}/"

restore_target_git
trap - EXIT

echo "Public repository sync completed."
