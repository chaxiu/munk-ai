#!/usr/bin/env bash
# Materialize Cloudflare R2 publish env file for CI.
#
# Required environment variables:
#   R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
#   R2_BUCKET_NAME, R2_PUBLIC_BASE_URL
#
# Optional:
#   R2_REGION (default: auto)
#   R2_CHANNEL (default: stable)
#   R2_PREFIX (default: empty)
#   MUNK_R2_ENV_PATH — output file path
#
# Prints the absolute path of the env file to stdout (last line).
set -euo pipefail

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "missing required environment variable: ${name}" >&2
    exit 1
  fi
}

for key in \
  R2_ACCOUNT_ID \
  R2_ACCESS_KEY_ID \
  R2_SECRET_ACCESS_KEY \
  R2_BUCKET_NAME \
  R2_PUBLIC_BASE_URL
do
  require_env "$key"
done

if [[ -n "${MUNK_R2_ENV_PATH:-}" ]]; then
  ENV_PATH="${MUNK_R2_ENV_PATH}"
elif [[ -n "${RUNNER_TEMP:-}" ]]; then
  ENV_PATH="${RUNNER_TEMP}/munk-r2.env"
else
  ENV_PATH="$(mktemp "${TMPDIR:-/tmp}/munk-r2.XXXXXX.env")"
fi

mkdir -p "$(dirname "${ENV_PATH}")"

cat > "${ENV_PATH}" <<EOF
R2_ACCOUNT_ID=${R2_ACCOUNT_ID}
R2_ACCESS_KEY_ID=${R2_ACCESS_KEY_ID}
R2_SECRET_ACCESS_KEY=${R2_SECRET_ACCESS_KEY}
R2_BUCKET_NAME=${R2_BUCKET_NAME}
R2_PUBLIC_BASE_URL=${R2_PUBLIC_BASE_URL}
R2_REGION=${R2_REGION:-auto}
R2_CHANNEL=${R2_CHANNEL:-stable}
R2_PREFIX=${R2_PREFIX:-}
EOF
chmod 600 "${ENV_PATH}"

echo "materialized R2 publish env at ${ENV_PATH}" >&2
printf '%s\n' "${ENV_PATH}"
