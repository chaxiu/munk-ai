#!/usr/bin/env bash
# Create or update a GitHub Release for the published runtime artifacts.
#
# Required env:
#   VERSION   - PEP440 version such as 0.34.0 or 0.34.0b1
#   CHANNEL   - stable | beta
# Optional env:
#   TAG       - release tag (default: v${VERSION})
#   ARTIFACT_DIR - directory with zip/tar.gz/sha256/release.json (default: dist/runtime-build/release-artifacts)
#   TARGET_SHA - commit SHA when creating a tag that does not already exist
#   GH_TOKEN / GITHUB_TOKEN - GitHub auth for gh
set -euo pipefail

VERSION="${VERSION:?VERSION is required}"
CHANNEL="${CHANNEL:?CHANNEL is required}"
TAG="${TAG:-v${VERSION}}"
ARTIFACT_DIR="${ARTIFACT_DIR:-dist/runtime-build/release-artifacts}"

if [[ ! -d "${ARTIFACT_DIR}" ]]; then
  echo "missing artifact directory: ${ARTIFACT_DIR}" >&2
  exit 1
fi

mapfile -t FILES < <(
  find "${ARTIFACT_DIR}" -maxdepth 1 -type f \( \
    -name '*.zip' -o -name '*.tar.gz' -o -name '*.sha256' -o -name '*.release.json' \
  \) | sort
)

if [[ "${#FILES[@]}" -eq 0 ]]; then
  echo "no release artifacts found in ${ARTIFACT_DIR}" >&2
  exit 1
fi

TITLE="munk ${VERSION}"
NOTES="$(
  cat <<EOF
## munk ${VERSION}

Channel: \`${CHANNEL}\`

Install:

\`\`\`bash
curl -fsSL https://downloads.munk.sh/install.sh | bash
\`\`\`

Primary distribution is Cloudflare R2 (\`downloads.munk.sh\`). This GitHub Release mirrors the same archives for browsing and manual download.
EOF
)"

CREATE_ARGS=(--title "${TITLE}" --notes "${NOTES}")
if [[ "${CHANNEL}" == "beta" ]]; then
  CREATE_ARGS+=(--prerelease --latest=false)
else
  CREATE_ARGS+=(--latest=true)
fi
if [[ -n "${TARGET_SHA:-}" ]]; then
  CREATE_ARGS+=(--target "${TARGET_SHA}")
fi

echo "Publishing GitHub Release ${TAG} (${CHANNEL}) with ${#FILES[@]} files"

if gh release view "${TAG}" >/dev/null 2>&1; then
  if [[ "${CHANNEL}" == "beta" ]]; then
    gh release edit "${TAG}" --title "${TITLE}" --notes "${NOTES}" --prerelease --latest=false
  else
    gh release edit "${TAG}" --title "${TITLE}" --notes "${NOTES}" --prerelease=false --latest=true
  fi
  gh release upload "${TAG}" "${FILES[@]}" --clobber
else
  gh release create "${TAG}" "${FILES[@]}" "${CREATE_ARGS[@]}"
fi

echo "GitHub Release published: ${TAG}"
gh release view "${TAG}" --json url,tagName,isPrerelease,isLatest,assets \
  --jq '{url, tagName, isPrerelease, isLatest, assets: [.assets[].name]}'
