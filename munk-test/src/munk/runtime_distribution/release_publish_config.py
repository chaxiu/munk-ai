from __future__ import annotations

import re
from pathlib import Path

from .release_publish_models import R2PublishConfig

PROJECT_VERSION_PATTERN = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$')
SUPPORTED_RELEASE_CHANNELS = {"stable", "beta"}
NON_FINAL_VERSION_PATTERN = re.compile(r"(?:[._-]?(?:a|b|rc)\d+|[._-]?dev\d+)(?:$|[.+-])", re.IGNORECASE)


def load_publish_config(config_path: Path) -> R2PublishConfig:
    payload = _parse_env_file(config_path)
    required_keys = [
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
        "R2_PUBLIC_BASE_URL",
    ]
    missing = [key for key in required_keys if not payload.get(key)]
    if missing:
        raise RuntimeError(f"missing R2 publish settings in {config_path}: {', '.join(missing)}")
    return R2PublishConfig(
        account_id=payload["R2_ACCOUNT_ID"],
        access_key_id=payload["R2_ACCESS_KEY_ID"],
        secret_access_key=payload["R2_SECRET_ACCESS_KEY"],
        bucket_name=payload["R2_BUCKET_NAME"],
        public_base_url=payload["R2_PUBLIC_BASE_URL"],
        region=payload.get("R2_REGION", "auto") or "auto",
        channel=payload.get("R2_CHANNEL", "stable") or "stable",
        prefix=payload.get("R2_PREFIX", ""),
    )


def load_release_version(project_root: Path) -> str:
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise RuntimeError(f"missing pyproject.toml: {pyproject_path}")
    in_project_section = False
    for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("["):
            in_project_section = line == "[project]"
            continue
        if not in_project_section:
            continue
        match = PROJECT_VERSION_PATTERN.match(raw_line)
        if match is not None:
            return match.group(1)
    raise RuntimeError(f"missing [project].version in {pyproject_path}")


def normalize_release_channel(channel: str) -> str:
    normalized = channel.strip().lower()
    if normalized not in SUPPORTED_RELEASE_CHANNELS:
        supported = ", ".join(sorted(SUPPORTED_RELEASE_CHANNELS))
        raise RuntimeError(f"unsupported release channel: {channel!r}; expected one of: {supported}")
    return normalized


def is_non_final_version(version: str) -> bool:
    return NON_FINAL_VERSION_PATTERN.search(version.strip()) is not None


def validate_release_channel_version(
    *,
    channel: str,
    version: str,
    allow_mismatch: bool = False,
) -> str:
    normalized_channel = normalize_release_channel(channel)
    if allow_mismatch:
        return normalized_channel
    non_final = is_non_final_version(version)
    if normalized_channel == "stable" and non_final:
        raise RuntimeError(
            f"stable releases must use a final version, got {version!r}; "
            "publish this version to the beta channel or pass --allow-channel-version-mismatch"
        )
    if normalized_channel == "beta" and not non_final:
        raise RuntimeError(
            f"beta releases must use a pre-release version such as '0.22.0b1', got {version!r}; "
            "publish final versions to the stable channel or pass --allow-channel-version-mismatch"
        )
    return normalized_channel


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise RuntimeError(f"missing config file: {path}")
    payload: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = _strip_shell_quotes(value.strip())
    return payload


def _strip_shell_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
