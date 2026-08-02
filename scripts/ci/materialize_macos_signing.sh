#!/usr/bin/env bash
# Materialize macOS codesign / notarization inputs for CI or local dry-runs.
#
# Required environment variables:
#   TEAM_ID, BUNDLE_ID, SIGNING_IDENTITY
#   ASC_KEY_ID, ASC_ISSUER_ID
#   ASC_API_KEY_P8          — raw .p8 contents (or use ASC_API_KEY_P8_BASE64)
#   P12_BASE64             — base64-encoded Developer ID Application .p12
#   P12_PASSWORD
#
# Optional:
#   MUNK_SIGNING_DIR       — output directory (default: $RUNNER_TEMP/munk-signing or mktemp)
#
# Writes:
#   $MUNK_SIGNING_DIR/signing.env
#   $MUNK_SIGNING_DIR/Certificates.p12
#   $MUNK_SIGNING_DIR/AuthKey.p8
#
# Prints the absolute path of signing.env to stdout (last line).
set -euo pipefail

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "missing required environment variable: ${name}" >&2
    exit 1
  fi
}

for key in \
  TEAM_ID \
  BUNDLE_ID \
  SIGNING_IDENTITY \
  ASC_KEY_ID \
  ASC_ISSUER_ID \
  P12_BASE64 \
  P12_PASSWORD
do
  require_env "$key"
done

if [[ -z "${ASC_API_KEY_P8:-}" && -z "${ASC_API_KEY_P8_BASE64:-}" ]]; then
  echo "missing required environment variable: ASC_API_KEY_P8 or ASC_API_KEY_P8_BASE64" >&2
  exit 1
fi

if [[ -n "${MUNK_SIGNING_DIR:-}" ]]; then
  SIGNING_DIR="${MUNK_SIGNING_DIR}"
elif [[ -n "${RUNNER_TEMP:-}" ]]; then
  SIGNING_DIR="${RUNNER_TEMP}/munk-signing"
else
  SIGNING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/munk-signing.XXXXXX")"
fi

mkdir -p "${SIGNING_DIR}"
chmod 700 "${SIGNING_DIR}"

P12_PATH="${SIGNING_DIR}/Certificates.p12"
ASC_KEY_PATH="${SIGNING_DIR}/AuthKey.p8"
SIGNING_ENV_PATH="${SIGNING_DIR}/signing.env"

printf '%s' "${P12_BASE64}" | base64 --decode > "${P12_PATH}"
chmod 600 "${P12_PATH}"

if [[ -n "${ASC_API_KEY_P8:-}" ]]; then
  printf '%s\n' "${ASC_API_KEY_P8}" > "${ASC_KEY_PATH}"
else
  printf '%s' "${ASC_API_KEY_P8_BASE64}" | base64 --decode > "${ASC_KEY_PATH}"
fi
chmod 600 "${ASC_KEY_PATH}"

cat > "${SIGNING_ENV_PATH}" <<EOF
TEAM_ID=${TEAM_ID}
BUNDLE_ID=${BUNDLE_ID}
SIGNING_IDENTITY=${SIGNING_IDENTITY}
ASC_KEY_ID=${ASC_KEY_ID}
ASC_ISSUER_ID=${ASC_ISSUER_ID}
ASC_KEY_PATH=${ASC_KEY_PATH}
P12_PATH=${P12_PATH}
P12_PASSWORD=${P12_PASSWORD}
EOF
chmod 600 "${SIGNING_ENV_PATH}"

echo "materialized macOS signing inputs under ${SIGNING_DIR}" >&2
printf '%s\n' "${SIGNING_ENV_PATH}"
