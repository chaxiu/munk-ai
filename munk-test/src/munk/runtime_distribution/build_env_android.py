from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from munk.runtime_distribution.build_env_downloads import download_with_proxy_support
from munk.runtime_distribution.build_env_platform import (
    resolve_android_platform_tools_target_platform,
    resolve_expected_adb_path,
)

ADB_VERSION_CONFIG_KEY = "android_platform_tools"
ADB_VERSION_FIELD = "version"
ADB_PLATFORMS_FIELD = "platforms"
ADB_URL_FIELD = "url"
ADB_SHA256_FIELD = "sha256"
ADB_VERSION_MARKER_FILE = ".munk-android-platform-tools-version"
SHA256_HEX_LENGTH = 64


@dataclass(frozen=True)
class AndroidPlatformToolsPin:
    version: str
    url: str
    sha256: str
    target_platform: str


def load_android_platform_tools_version(config_path: Path) -> str:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid runtime version config: expected object in {config_path}")
    payload_dict = cast(dict[str, Any], payload)
    adb_config = payload_dict.get(ADB_VERSION_CONFIG_KEY)
    if not isinstance(adb_config, dict):
        raise RuntimeError(f"invalid runtime version config: missing '{ADB_VERSION_CONFIG_KEY}' in {config_path}")
    adb_config_dict = cast(dict[str, Any], adb_config)
    version = adb_config_dict.get(ADB_VERSION_FIELD)
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"invalid runtime version config: bad {ADB_VERSION_FIELD} in {config_path}")
    return version.strip()


def load_android_platform_tools_pin(*, config_path: Path, target_platform: str) -> AndroidPlatformToolsPin:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid runtime version config: expected object in {config_path}")
    payload_dict = cast(dict[str, Any], payload)
    adb_config = payload_dict.get(ADB_VERSION_CONFIG_KEY)
    if not isinstance(adb_config, dict):
        raise RuntimeError(f"invalid runtime version config: missing '{ADB_VERSION_CONFIG_KEY}' in {config_path}")
    adb_config_dict = cast(dict[str, Any], adb_config)
    version = adb_config_dict.get(ADB_VERSION_FIELD)
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"invalid runtime version config: bad {ADB_VERSION_FIELD} in {config_path}")
    platforms = adb_config_dict.get(ADB_PLATFORMS_FIELD)
    if not isinstance(platforms, dict):
        raise RuntimeError(f"invalid runtime version config: missing {ADB_PLATFORMS_FIELD} in {config_path}")
    platforms_dict = cast(dict[str, Any], platforms)
    platform_config = platforms_dict.get(target_platform)
    if not isinstance(platform_config, dict):
        raise RuntimeError(
            f"invalid runtime version config: missing {ADB_PLATFORMS_FIELD}.{target_platform} in {config_path}"
        )
    platform_config_dict = cast(dict[str, Any], platform_config)
    url = platform_config_dict.get(ADB_URL_FIELD)
    sha256 = platform_config_dict.get(ADB_SHA256_FIELD)
    if not isinstance(url, str) or not url.strip():
        raise RuntimeError(
            f"invalid runtime version config: bad {ADB_PLATFORMS_FIELD}.{target_platform}.{ADB_URL_FIELD} in {config_path}"
        )
    if not isinstance(sha256, str) or len(sha256.strip()) != SHA256_HEX_LENGTH:
        raise RuntimeError(
            f"invalid runtime version config: bad {ADB_PLATFORMS_FIELD}.{target_platform}.{ADB_SHA256_FIELD} in {config_path}"
        )
    return AndroidPlatformToolsPin(
        version=version.strip(),
        url=url.strip(),
        sha256=sha256.strip().lower(),
        target_platform=target_platform,
    )


def extract_android_platform_tools_archive(
    *,
    archive_path: Path,
    destination_root: Path,
    target_platform: str,
) -> None:
    platform_tools_dir = destination_root / "platform-tools"
    if platform_tools_dir.exists():
        shutil.rmtree(platform_tools_dir)
    destination_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="munk-android-platform-tools-") as temp_dir:
        temp_root = Path(temp_dir)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(temp_root)
        extracted_root = temp_root / "platform-tools"
        if not extracted_root.exists():
            raise RuntimeError(f"unexpected platform-tools archive layout: {archive_path}")
        shutil.move(str(extracted_root), str(platform_tools_dir))
    adb_path = resolve_expected_adb_path(platform_root=destination_root, target_platform=target_platform)
    if not adb_path.exists():
        raise RuntimeError(f"missing adb after extracting platform-tools archive: {adb_path}")


def verify_android_platform_tools_archive(*, archive_path: Path, expected_sha256: str) -> None:
    actual_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"android platform-tools archive sha256 mismatch: expected={expected_sha256} actual={actual_sha256} path={archive_path}"
        )


def verify_android_platform_tools_installation(*, platform_root: Path, target_platform: str, version: str) -> None:
    adb_path = resolve_expected_adb_path(platform_root=platform_root, target_platform=target_platform)
    if not adb_path.exists():
        raise RuntimeError(f"downloaded platform-tools archive did not contain adb: {adb_path}")
    source_properties = platform_root / "platform-tools" / "source.properties"
    if not source_properties.exists():
        raise RuntimeError(f"missing source.properties after extracting platform-tools archive: {source_properties}")
    revision = None
    for line in source_properties.read_text(encoding="utf-8").splitlines():
        if line.startswith("Pkg.Revision="):
            revision = line.split("=", 1)[1].strip()
            break
    if revision != version:
        raise RuntimeError(
            f"android platform-tools extracted revision mismatch: expected={version} actual={revision} path={source_properties}"
        )


def install_android_platform_tools(
    *,
    pin: AndroidPlatformToolsPin,
    target_platform: str,
    download_dir: Path,
    destination_root: Path,
    force: bool = False,
) -> Path:
    if pin.target_platform != target_platform:
        raise RuntimeError(
            f"android platform-tools pin target mismatch: pin={pin.target_platform} requested={target_platform}"
        )
    platform_root = destination_root / target_platform
    version_marker = platform_root / ADB_VERSION_MARKER_FILE
    adb_path = resolve_expected_adb_path(platform_root=platform_root, target_platform=target_platform)
    if (
        not force
        and adb_path.exists()
        and version_marker.exists()
        and version_marker.read_text(encoding="utf-8").strip() == pin.version
    ):
        verify_android_platform_tools_installation(platform_root=platform_root, target_platform=target_platform, version=pin.version)
        return adb_path

    download_dir.mkdir(parents=True, exist_ok=True)
    archive_path = download_dir / Path(pin.url).name
    if force or not archive_path.exists():
        print(f"downloading android platform-tools: {pin.url}")
        download_with_proxy_support(url=pin.url, destination=archive_path)
    verify_android_platform_tools_archive(archive_path=archive_path, expected_sha256=pin.sha256)
    extract_android_platform_tools_archive(
        archive_path=archive_path,
        destination_root=platform_root,
        target_platform=target_platform,
    )
    verify_android_platform_tools_installation(platform_root=platform_root, target_platform=target_platform, version=pin.version)
    version_marker.parent.mkdir(parents=True, exist_ok=True)
    version_marker.write_text(f"{pin.version}\n", encoding="utf-8")
    if target_platform != "windows":
        adb_path.chmod(0o755)
    return adb_path


def copy_adb_sidecar(
    *,
    project_root: Path,
    runtime_root: Path,
    download_dir: Path,
    pin: AndroidPlatformToolsPin,
    target_platform: str = "auto",
) -> Path:
    resolved_target_platform = resolve_android_platform_tools_target_platform(target_platform)
    if pin.target_platform != resolved_target_platform:
        raise RuntimeError(
            f"android platform-tools pin target mismatch: pin={pin.target_platform} requested={resolved_target_platform}"
        )
    cached_adb_path = install_android_platform_tools(
        pin=pin,
        target_platform=resolved_target_platform,
        download_dir=download_dir,
        destination_root=project_root / "android-adb",
    )
    sidecar_target = runtime_root / "sidecars" / "android-adb" / "platform-tools"
    sidecar_target.parent.mkdir(parents=True, exist_ok=True)
    source = cached_adb_path.parent
    if not source.exists():
        raise RuntimeError(f"missing adb sidecar source: {source}")
    if sidecar_target.exists():
        shutil.rmtree(sidecar_target)
    shutil.copytree(source, sidecar_target)
    adb_path = resolve_expected_adb_path(platform_root=sidecar_target.parent, target_platform=resolved_target_platform)
    if not adb_path.exists():
        raise RuntimeError(f"copied adb sidecar is missing adb executable: {adb_path}")
    return adb_path
