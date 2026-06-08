from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.request import Request, urlopen

DEFAULT_ICON_MODEL_MANIFEST_URL = "https://downloads.munk.sh/models/detect/detect.json"
ICON_MODEL_CONFIG_KEY = "icon_detect_model"
USER_AGENT = "munk-perception-full-build-helper/1.0"
_RUNTIME_VERSION_CONFIG_RELPATH = Path("config") / "build" / "runtime-version.json"


@dataclass(frozen=True)
class IconModelRelease:
    name: str
    version: str
    url: str
    sha256: str
    manifest_url: str | None = None


def project_root() -> Path:
    return Path(__file__).resolve().parent


def workspace_root() -> Path:
    for candidate in (project_root(), *project_root().parents):
        if (candidate / _RUNTIME_VERSION_CONFIG_RELPATH).exists():
            return candidate
    # Fall back to the repo root implied by the current package layout.
    return Path(__file__).resolve().parents[3]


DEFAULT_RUNTIME_VERSION_CONFIG = workspace_root() / _RUNTIME_VERSION_CONFIG_RELPATH


def runtime_model_path(root: Path | None = None) -> Path:
    base = project_root() if root is None else root
    return base / "src" / "munk_perception_full" / "resources" / "models" / "detect" / "detect.onnx"


def prepare_icon_model(
    root: Path | None = None,
    *,
    version_config_path: Path = DEFAULT_RUNTIME_VERSION_CONFIG,
    manifest_url: str | None = None,
    force: bool = False,
) -> Path:
    base = project_root() if root is None else root
    model_path = runtime_model_path(base)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    release = load_icon_model_release(version_config_path=version_config_path, manifest_url=manifest_url)
    if model_path.exists() and not force and _matches_expected_sha256(model_path, release.sha256):
        return model_path
    payload = _download_bytes(release.url)
    if not payload:
        raise ValueError(f"downloaded icon model is empty: {release.url}")
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != release.sha256:
        raise ValueError(
            f"downloaded icon model sha256 mismatch: expected={release.sha256} actual={actual_sha256} url={release.url}"
        )
    model_path.write_bytes(payload)
    return model_path


def load_icon_model_release(*, version_config_path: Path = DEFAULT_RUNTIME_VERSION_CONFIG, manifest_url: str | None = None) -> IconModelRelease:
    payload = json.loads(version_config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid runtime version config: expected object in {version_config_path}")
    payload_dict = cast(dict[str, Any], payload)
    model_config = payload_dict.get(ICON_MODEL_CONFIG_KEY)
    if not isinstance(model_config, dict):
        raise RuntimeError(f"invalid runtime version config: missing '{ICON_MODEL_CONFIG_KEY}' in {version_config_path}")
    model_config_dict = cast(dict[str, Any], model_config)
    pinned = _icon_model_release_from_payload(
        model_config_dict,
        manifest_url=manifest_url or cast(str | None, model_config_dict.get("manifest_url")),
    )
    if pinned.manifest_url is None:
        return pinned
    remote_payload = _load_json(pinned.manifest_url)
    remote = _icon_model_release_from_payload(remote_payload, manifest_url=pinned.manifest_url)
    if remote != pinned:
        raise RuntimeError(
            "remote icon model manifest does not match pinned runtime version config: "
            f"pinned={pinned} remote={remote}"
        )
    return pinned


def _icon_model_release_from_payload(payload: object, *, manifest_url: str | None) -> IconModelRelease:
    if not isinstance(payload, dict):
        raise RuntimeError("invalid icon model release payload: expected object")
    payload_dict = cast(dict[str, Any], payload)
    name = payload_dict.get("name")
    version = payload_dict.get("version")
    url = payload_dict.get("url")
    sha256 = payload_dict.get("sha256")
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError("invalid icon model release payload: bad name")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("invalid icon model release payload: bad version")
    if not isinstance(url, str) or not url.strip():
        raise RuntimeError("invalid icon model release payload: bad url")
    if not isinstance(sha256, str) or len(sha256.strip()) != 64:
        raise RuntimeError("invalid icon model release payload: bad sha256")
    return IconModelRelease(
        name=name.strip(),
        version=version.strip(),
        url=url.strip(),
        sha256=sha256.strip().lower(),
        manifest_url=manifest_url.strip() if isinstance(manifest_url, str) and manifest_url.strip() else None,
    )


def _load_json(url: str) -> object:
    return json.loads(_download_bytes(url).decode("utf-8"))


def _download_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request) as response:  # noqa: S310
        return response.read()


def _matches_expected_sha256(path: Path, expected_sha256: str) -> bool:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest == expected_sha256


def main() -> int:
    parser = argparse.ArgumentParser(description="Build helpers for perception-sdk-full")
    parser.add_argument(
        "command",
        choices=("prepare-icon-model",),
        help="Download runtime resources required by builds.",
    )
    parser.add_argument(
        "--version-config",
        type=Path,
        default=DEFAULT_RUNTIME_VERSION_CONFIG,
        help="Path to the runtime version config containing icon_detect_model metadata.",
    )
    parser.add_argument(
        "--manifest-url",
        default=None,
        help="Optional override for the remote icon model manifest URL.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download the icon model even if the local runtime resource already exists.",
    )
    args = parser.parse_args()
    if args.command == "prepare-icon-model":
        path = prepare_icon_model(
            version_config_path=args.version_config.resolve(),
            manifest_url=args.manifest_url,
            force=args.force,
        )
        print(f"prepared icon model: {path}")
        return 0
    raise RuntimeError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
