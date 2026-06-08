#!/usr/bin/env bash
set -euo pipefail

CHANNEL="stable"
VERSION=""
VARIANT="full"
INSTALL_DIR="${HOME}/.local/share/munk"
BIN_DIR="${HOME}/.local/bin"
BASE_URL="https://downloads.munk.sh"

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Options:
  --channel <channel>       Release channel to install (default: stable)
  --version <version>       Install an explicit version instead of the current channel
  --variant <variant>       Runtime variant to install (default: full)
  --install-dir <path>      Runtime install root (default: ~/.local/share/munk)
  --bin-dir <path>          Symlink directory for munk launcher (default: ~/.local/bin)
  --base-url <url>          Download manifest base URL (default: https://downloads.munk.sh)
  -h, --help                Show this help text
EOF
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "missing required command: ${command_name}" >&2
    exit 1
  fi
}

download_file() {
  local url="$1"
  local output_path="$2"
  local mode="${3:-quiet}"
  local label="${4:-download}"

  if [[ "$mode" == "progress" ]]; then
    download_file_with_progress "$url" "$output_path" "$label"
    return
  fi

  curl -fsSL "$url" -o "$output_path"
}

resolve_content_length() {
  local url="$1"
  local content_length
  content_length="$(
    curl -fsSLI "$url" 2>/dev/null | awk '
      BEGIN { IGNORECASE = 1 }
      /^content-length:/ {
        gsub("\r", "", $2)
        value = $2
      }
      END {
        if (value ~ /^[0-9]+$/) {
          print value
        }
      }
    '
  )"
  if [[ "$content_length" =~ ^[0-9]+$ && "$content_length" -gt 0 ]]; then
    printf '%s\n' "$content_length"
    return 0
  fi
  return 1
}

current_file_size() {
  local file_path="$1"
  if [[ ! -f "$file_path" ]]; then
    printf '0\n'
    return
  fi
  wc -c < "$file_path" | tr -d '[:space:]'
}

format_bytes() {
  local bytes="$1"
  awk -v bytes="$bytes" '
    BEGIN {
      split("B KiB MiB GiB TiB PiB", units, " ")
      value = bytes + 0
      unit_index = 1
      while (value >= 1024 && unit_index < 6) {
        value /= 1024
        unit_index += 1
      }
      if (unit_index == 1) {
        printf "%d %s", value, units[unit_index]
      } else {
        printf "%.1f %s", value, units[unit_index]
      }
    }
  '
}

render_progress_message() {
  local label="$1"
  local current_size="$2"
  local total_size="${3:-}"
  local current_human
  current_human="$(format_bytes "$current_size")"

  if [[ -n "$total_size" && "$total_size" -gt 0 ]]; then
    local bounded_current percent_tenths total_human
    bounded_current="$current_size"
    if [[ "$bounded_current" -gt "$total_size" ]]; then
      bounded_current="$total_size"
    fi
    percent_tenths=$(( bounded_current * 1000 / total_size ))
    total_human="$(format_bytes "$total_size")"
    printf '%s: %d.%d%% (%s / %s)' \
      "$label" \
      $(( percent_tenths / 10 )) \
      $(( percent_tenths % 10 )) \
      "$current_human" \
      "$total_human"
    return
  fi

  printf '%s: %s downloaded' "$label" "$current_human"
}

download_file_with_progress() {
  local url="$1"
  local output_path="$2"
  local label="$3"
  local total_size=""
  local current_size=0
  local last_percent_bucket=-1
  local last_reported_size=0

  total_size="$(resolve_content_length "$url" || true)"

  rm -f "$output_path"
  curl -fsSL "$url" -o "$output_path" &
  local curl_pid=$!

  while kill -0 "$curl_pid" >/dev/null 2>&1; do
    current_size="$(current_file_size "$output_path")"
    if [[ -t 2 ]]; then
      printf '\r%s' "$(render_progress_message "$label" "$current_size" "$total_size")" >&2
    else
      if [[ -n "$total_size" && "$total_size" -gt 0 ]]; then
        local percent_bucket
        percent_bucket=$(( current_size * 100 / total_size ))
        if [[ "$percent_bucket" -ge $(( last_percent_bucket + 5 )) ]]; then
          printf '%s\n' "$(render_progress_message "$label" "$current_size" "$total_size")" >&2
          last_percent_bucket="$percent_bucket"
        fi
      elif [[ $(( current_size - last_reported_size )) -ge $(( 20 * 1024 * 1024 )) ]]; then
        printf '%s\n' "$(render_progress_message "$label" "$current_size")" >&2
        last_reported_size="$current_size"
      fi
    fi
    sleep 1
  done

  if ! wait "$curl_pid"; then
    if [[ -t 2 ]]; then
      printf '\n' >&2
    fi
    return 1
  fi

  current_size="$(current_file_size "$output_path")"
  if [[ -t 2 ]]; then
    printf '\r%s\n' "$(render_progress_message "$label" "$current_size" "$total_size")" >&2
  elif [[ -n "$total_size" && "$total_size" -gt 0 ]]; then
    if [[ "$last_percent_bucket" -lt 100 ]]; then
      printf '%s\n' "$(render_progress_message "$label" "$current_size" "$total_size")" >&2
    fi
  elif [[ "$current_size" -gt "$last_reported_size" ]]; then
    printf '%s\n' "$(render_progress_message "$label" "$current_size")" >&2
  fi
}

is_dir_on_path() {
  local dir_path="$1"
  [[ ":${PATH}:" == *":${dir_path}:"* ]]
}

display_path() {
  local path_value="$1"
  if [[ "$path_value" == "$HOME" ]]; then
    printf '~\n'
    return
  fi
  if [[ "$path_value" == "$HOME/"* ]]; then
    printf '~/%s\n' "${path_value#"$HOME"/}"
    return
  fi
  printf '%s\n' "$path_value"
}

current_shell_name() {
  printf '%s\n' "${SHELL##*/}"
}

resolve_shell_profile() {
  local shell_name
  shell_name="$(current_shell_name)"
  case "$shell_name" in
    zsh)
      printf '%s\n' "${ZDOTDIR:-$HOME}/.zshrc"
      ;;
    bash)
      if [[ -f "${HOME}/.bash_profile" ]]; then
        printf '%s\n' "${HOME}/.bash_profile"
      else
        printf '%s\n' "${HOME}/.bashrc"
      fi
      ;;
    *)
      return 1
      ;;
  esac
}

can_prompt_on_tty() {
  [[ -t 2 && -e /dev/tty && -r /dev/tty && -w /dev/tty ]]
}

confirm_path_update() {
  local profile_path="$1"
  local shell_name="$2"
  local answer
  if ! can_prompt_on_tty; then
    return 1
  fi
  printf 'detected shell: %s\n' "$shell_name" > /dev/tty
  printf 'detected shell profile: %s\n' "$(display_path "$profile_path")" > /dev/tty
  printf 'munk installs its launcher to %s.\n' "$(display_path "$BIN_DIR")" > /dev/tty
  printf 'add it to PATH now? [y/N] ' > /dev/tty
  if ! IFS= read -r answer < /dev/tty; then
    return 1
  fi
  [[ "$answer" == "y" || "$answer" == "Y" ]]
}

ensure_path_in_profile() {
  local profile_path="$1"
  local marker_start="# >>> munk path >>>"
  local marker_end="# <<< munk path <<<"
  local export_line="export PATH=\"${BIN_DIR}:\$PATH\""

  mkdir -p "$(dirname "$profile_path")"
  touch "$profile_path"
  if grep -Fq "$marker_start" "$profile_path" || grep -Fq "$export_line" "$profile_path"; then
    return 0
  fi
  {
    printf '\n%s\n' "$marker_start"
    printf '%s\n' "$export_line"
    printf '%s\n' "$marker_end"
  } >> "$profile_path"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --channel)
        CHANNEL="$2"
        shift 2
        ;;
      --version)
        VERSION="$2"
        shift 2
        ;;
      --variant)
        VARIANT="$2"
        shift 2
        ;;
      --install-dir)
        INSTALL_DIR="$2"
        shift 2
        ;;
      --bin-dir)
        BIN_DIR="$2"
        shift 2
        ;;
      --base-url)
        BASE_URL="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "unknown argument: $1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
}

detect_target() {
  local os_name arch_name
  os_name="$(uname -s)"
  arch_name="$(uname -m)"
  if [[ "$os_name" != "Darwin" ]]; then
    echo "munk installer currently supports macOS only" >&2
    exit 1
  fi
  case "$arch_name" in
    arm64|aarch64)
      TARGET_KEY="darwin-arm64"
      ;;
    x86_64|amd64)
      echo "munk installer currently supports macOS ARM64 only" >&2
      exit 1
      ;;
    *)
      echo "unsupported macOS architecture: ${arch_name}" >&2
      exit 1
      ;;
  esac
}

resolve_manifest_url() {
  local normalized_base_url
  normalized_base_url="${BASE_URL%/}"
  if [[ -n "$VERSION" ]]; then
    MANIFEST_URL="${normalized_base_url}/releases/v${VERSION}/version.json"
  else
    MANIFEST_URL="${normalized_base_url}/channels/${CHANNEL}.json"
  fi
}

manifest_value() {
  local expression="$1"
  local target_key="$2"
  local variant="$3"
  python3 - "$MANIFEST_PATH" "$expression" "$target_key" "$variant" <<'PY'
import json
import sys

manifest_path = sys.argv[1]
expression = sys.argv[2]
with open(manifest_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

if expression == "version":
    value = payload.get("version", "")
else:
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SystemExit(2)
    target_key = artifacts.get(sys.argv[3], {})
    if not isinstance(target_key, dict):
        raise SystemExit(2)
    variant_payload = target_key.get(sys.argv[4])
    if not isinstance(variant_payload, dict):
        raise SystemExit(2)
    if expression == "archive_url":
        value = variant_payload.get("archive_url", "")
    elif expression == "sha256_url":
        value = variant_payload.get("sha256_url", "")
    elif expression == "sha256":
        value = variant_payload.get("sha256", "")
    elif expression == "filename":
        value = variant_payload.get("filename", "")
    else:
        raise SystemExit(3)

if not isinstance(value, str) or not value:
    raise SystemExit(4)
print(value)
PY
}

extract_runtime_root() {
  local extracted_root
  extracted_root="$(find "$1" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  if [[ -z "$extracted_root" ]]; then
    echo "installer could not locate extracted runtime root" >&2
    exit 1
  fi
  printf '%s\n' "$extracted_root"
}

verify_checksum() {
  local expected actual
  expected="$(awk '{print $1}' "$SHA256_PATH")"
  actual="$(shasum -a 256 "$ARCHIVE_PATH" | awk '{print $1}')"
  if [[ "$expected" != "$actual" ]]; then
    echo "archive checksum mismatch" >&2
    exit 1
  fi
  if [[ -n "$MANIFEST_SHA256" && "$expected" != "$MANIFEST_SHA256" ]]; then
    echo "manifest checksum does not match downloaded checksum file" >&2
    exit 1
  fi
}

main() {
  parse_args "$@"
  require_command curl
  require_command python3
  require_command shasum
  require_command mktemp
  require_command find
  require_command awk
  detect_target
  resolve_manifest_url

  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT

  MANIFEST_PATH="${TMP_DIR}/version.json"
  echo "fetching manifest: ${MANIFEST_URL}"
  download_file "$MANIFEST_URL" "$MANIFEST_PATH"

  if ! RESOLVED_VERSION="$(manifest_value version "$TARGET_KEY" "$VARIANT" 2>/dev/null)"; then
    echo "installer could not read version from manifest" >&2
    exit 1
  fi
  if ! ARCHIVE_URL="$(manifest_value archive_url "$TARGET_KEY" "$VARIANT" 2>/dev/null)"; then
    echo "no artifact found for target=${TARGET_KEY} variant=${VARIANT}" >&2
    exit 1
  fi
  if ! SHA256_URL="$(manifest_value sha256_url "$TARGET_KEY" "$VARIANT" 2>/dev/null)"; then
    echo "missing checksum url for target=${TARGET_KEY} variant=${VARIANT}" >&2
    exit 1
  fi
  if ! ARCHIVE_FILENAME="$(manifest_value filename "$TARGET_KEY" "$VARIANT" 2>/dev/null)"; then
    echo "missing archive filename for target=${TARGET_KEY} variant=${VARIANT}" >&2
    exit 1
  fi
  MANIFEST_SHA256="$(manifest_value sha256 "$TARGET_KEY" "$VARIANT" 2>/dev/null || true)"

  ARCHIVE_PATH="${TMP_DIR}/${ARCHIVE_FILENAME}"
  SHA256_PATH="${TMP_DIR}/${ARCHIVE_FILENAME}.sha256"
  EXTRACT_DIR="${TMP_DIR}/extract"
  STAGING_DIR="${TMP_DIR}/staging"
  VERSIONS_DIR="${INSTALL_DIR}/versions"
  VERSION_DIR="${INSTALL_DIR}/versions/${RESOLVED_VERSION}-${VARIANT}"
  STAGED_VERSION_DIR="${VERSIONS_DIR}/.${RESOLVED_VERSION}-${VARIANT}.tmp.$$"
  BACKUP_VERSION_DIR="${VERSIONS_DIR}/.${RESOLVED_VERSION}-${VARIANT}.backup.$$"

  mkdir -p "$EXTRACT_DIR" "$STAGING_DIR" "$VERSIONS_DIR" "$BIN_DIR"

  echo "downloading archive: ${ARCHIVE_URL}"
  download_file "$ARCHIVE_URL" "$ARCHIVE_PATH" progress "archive"
  echo "downloading checksum: ${SHA256_URL}"
  download_file "$SHA256_URL" "$SHA256_PATH"
  verify_checksum

  echo "extracting runtime"
  ditto -x -k "$ARCHIVE_PATH" "$EXTRACT_DIR"
  EXTRACTED_ROOT="$(extract_runtime_root "$EXTRACT_DIR")"
  mv "$EXTRACTED_ROOT" "$STAGING_DIR/runtime"

  rm -rf "$STAGED_VERSION_DIR" "$BACKUP_VERSION_DIR"
  mv "$STAGING_DIR/runtime" "$STAGED_VERSION_DIR"
  if [[ -e "$VERSION_DIR" ]]; then
    mv "$VERSION_DIR" "$BACKUP_VERSION_DIR"
  fi
  if ! mv "$STAGED_VERSION_DIR" "$VERSION_DIR"; then
    rm -rf "$STAGED_VERSION_DIR"
    if [[ -e "$BACKUP_VERSION_DIR" ]]; then
      mv "$BACKUP_VERSION_DIR" "$VERSION_DIR" || true
    fi
    echo "failed to activate runtime at ${VERSION_DIR}" >&2
    exit 1
  fi
  rm -rf "$BACKUP_VERSION_DIR"
  ln -sfn "$VERSION_DIR" "${INSTALL_DIR}/current"
  ln -sfn "${INSTALL_DIR}/current/bin/munk" "${BIN_DIR}/munk"

  echo "installed munk ${RESOLVED_VERSION} (${VARIANT})"
  echo "runtime root: ${VERSION_DIR}"
  echo "launcher: ${BIN_DIR}/munk"
  VERIFY_COMMAND_PREFIX="${BIN_DIR}/munk"
  SHELL_PROFILE_PATH=""
  SHELL_NAME="$(current_shell_name)"
  if ! is_dir_on_path "$BIN_DIR"; then
    SHELL_PROFILE_PATH="$(resolve_shell_profile 2>/dev/null || true)"
    if [[ -n "$SHELL_PROFILE_PATH" ]] && confirm_path_update "$SHELL_PROFILE_PATH" "$SHELL_NAME"; then
      ensure_path_in_profile "$SHELL_PROFILE_PATH"
      echo "updated shell profile: $(display_path "$SHELL_PROFILE_PATH")"
      echo "reload your shell to use 'munk' directly:"
      echo "  source $(display_path "$SHELL_PROFILE_PATH")"
    fi
  fi
  if is_dir_on_path "$BIN_DIR"; then
    VERIFY_COMMAND_PREFIX="munk"
  else
    echo "note: $(display_path "$BIN_DIR") is not currently on PATH"
    if [[ -n "$SHELL_PROFILE_PATH" ]]; then
      echo "detected shell: ${SHELL_NAME}"
      echo "detected shell profile: $(display_path "$SHELL_PROFILE_PATH")"
    fi
    echo "add this to your shell profile if needed:"
    echo "  export PATH=\"${BIN_DIR}:\$PATH\""
  fi
  echo "verify with:"
  echo "  ${VERIFY_COMMAND_PREFIX} --help"
  echo "  ${VERIFY_COMMAND_PREFIX} version"
}

main "$@"
