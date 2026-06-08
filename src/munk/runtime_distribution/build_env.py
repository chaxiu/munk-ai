from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

SCRCPY_SERVER_VERSION = "3.3.3"
SCRCPY_SERVER_RELEASE_URL = (
    f"https://github.com/Genymobile/scrcpy/releases/download/v{SCRCPY_SERVER_VERSION}/"
    f"scrcpy-server-v{SCRCPY_SERVER_VERSION}"
)
NODE_RUNTIME_VERSION = "v24.4.1"
NODE_RUNTIME_VERSION_MARKER_FILE = ".munk-node-runtime-version"
ADB_VERSION_CONFIG_KEY = "android_platform_tools"
ADB_VERSION_FIELD = "version"
ADB_PLATFORMS_FIELD = "platforms"
ADB_URL_FIELD = "url"
ADB_SHA256_FIELD = "sha256"
ADB_VERSION_MARKER_FILE = ".munk-android-platform-tools-version"
PLATFORM_TO_REPOSITORY_SUFFIX = {
    "macos": "darwin",
    "linux": "linux",
    "windows": "win",
}


@dataclass(frozen=True)
class RuntimeVersionDefaults:
    release_tag: str
    python_version: str
    archive_flavor: str


@dataclass(frozen=True)
class AndroidPlatformToolsPin:
    version: str
    url: str
    sha256: str
    target_platform: str


@dataclass(frozen=True)
class DependencyProject:
    name: str
    project_dir: Path


@dataclass(frozen=True)
class RecordingSourceAssetPaths:
    workspace_root: Path
    workspace_package_json: Path
    workspace_lockfile: Path
    workspace_manifest: Path
    workspace_node_modules: Path
    workspace_pnpm_store: Path
    recording_web_dir: Path
    recording_web_dist: Path
    recording_bridge_dir: Path
    recording_bridge_dist: Path
    recording_bridge_node_modules: Path
    recording_bridge_package_json: Path
    recording_bridge_server_bin: Path


@dataclass(frozen=True)
class RecordingRuntimeAssetPaths:
    recording_ui_dir: Path
    recording_bridge_dir: Path
    sidecars_node_modules_dir: Path
    sidecars_pnpm_store: Path
    node_dir: Path
    node_bin: Path
    node_version_marker: Path


def load_runtime_version_defaults(config_path: Path) -> RuntimeVersionDefaults:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid runtime version config: expected object in {config_path}")
    payload_dict = cast(dict[str, Any], payload)
    pbs = payload_dict.get("python_build_standalone")
    if not isinstance(pbs, dict):
        raise RuntimeError(f"invalid runtime version config: missing 'python_build_standalone' in {config_path}")
    pbs_dict = cast(dict[str, Any], pbs)
    release_tag = pbs_dict.get("release_tag")
    python_version = pbs_dict.get("python_version")
    archive_flavor = pbs_dict.get("archive_flavor")
    if not isinstance(release_tag, str) or not release_tag:
        raise RuntimeError(f"invalid runtime version config: bad release_tag in {config_path}")
    if not isinstance(python_version, str) or not python_version:
        raise RuntimeError(f"invalid runtime version config: bad python_version in {config_path}")
    if not isinstance(archive_flavor, str) or not archive_flavor:
        raise RuntimeError(f"invalid runtime version config: bad archive_flavor in {config_path}")
    return RuntimeVersionDefaults(
        release_tag=release_tag,
        python_version=python_version,
        archive_flavor=archive_flavor,
    )


def ensure_supported_platform() -> None:
    if platform.system() != "Darwin":
        raise RuntimeError("standalone runtime scripts currently support macOS only")
    machine = normalized_arch()
    if machine not in {"arm64", "x86_64"}:
        raise RuntimeError(f"unsupported macOS architecture: {machine}")


def normalized_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    return machine


def pbs_target_triple() -> str:
    if normalized_arch() == "arm64":
        return "aarch64-apple-darwin"
    return "x86_64-apple-darwin"


def build_pinned_pbs_url(*, defaults: RuntimeVersionDefaults) -> str:
    asset_name = (
        f"cpython-{defaults.python_version}+{defaults.release_tag}-"
        f"{pbs_target_triple()}-{defaults.archive_flavor}.tar.gz"
    )
    return (
        "https://github.com/astral-sh/python-build-standalone/releases/download/"
        f"{defaults.release_tag}/{asset_name}"
    )


def resolve_pbs_archive(*, download_dir: Path, defaults: RuntimeVersionDefaults) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    url = build_pinned_pbs_url(defaults=defaults)
    destination = download_dir / Path(url).name
    if not destination.exists():
        print(f"downloading python-build-standalone: {url}")
        urllib.request.urlretrieve(url, destination)  # noqa: S310
    return destination


def extract_pbs_archive(*, archive_path: Path, python_root: Path, cwd: Path) -> None:
    if python_root.exists():
        shutil.rmtree(python_root)
    python_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="munk-pbs-extract-") as temp_dir:
        temp_path = Path(temp_dir)
        run_command(["tar", "-axf", str(archive_path), "-C", str(temp_path)], cwd=cwd)
        extracted = normalize_extracted_root(temp_path)
        for child in extracted.iterdir():
            destination = python_root / child.name
            if destination.exists():
                if destination.is_dir():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()
            shutil.move(str(child), str(destination))


def normalize_extracted_root(extract_root: Path) -> Path:
    children = [child for child in extract_root.iterdir() if child.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_root


def find_runtime_python(python_root: Path) -> Path:
    for candidate in [python_root / "bin" / "python3", python_root / "bin" / "python"]:
        if candidate.exists():
            return candidate
    raise RuntimeError(f"could not find runtime python in {python_root / 'bin'}")


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
    if not isinstance(sha256, str) or len(sha256.strip()) != 64:
        raise RuntimeError(
            f"invalid runtime version config: bad {ADB_PLATFORMS_FIELD}.{target_platform}.{ADB_SHA256_FIELD} in {config_path}"
        )
    return AndroidPlatformToolsPin(
        version=version.strip(),
        url=url.strip(),
        sha256=sha256.strip().lower(),
        target_platform=target_platform,
    )


def resolve_android_platform_tools_target_platform(requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    system = platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Linux":
        return "linux"
    if system == "Windows":
        return "windows"
    raise RuntimeError(f"unsupported host platform for android platform-tools: {system}")


def build_android_platform_tools_url(*, version: str, target_platform: str) -> str:
    suffix = PLATFORM_TO_REPOSITORY_SUFFIX.get(target_platform)
    if suffix is None:
        raise RuntimeError(f"unsupported android platform-tools target platform: {target_platform}")
    asset_name = f"platform-tools_r{version}-{suffix}.zip"
    return f"https://dl.google.com/android/repository/{asset_name}"


def resolve_expected_adb_path(*, platform_root: Path, target_platform: str) -> Path:
    executable_name = "adb.exe" if target_platform == "windows" else "adb"
    return platform_root / "platform-tools" / executable_name


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


def download_with_proxy_support(*, url: str, destination: Path) -> None:
    if _curl_available():
        try:
            _download_with_curl(url=url, destination=destination)
            return
        except RuntimeError as exc:
            print(f"warning: curl download failed, falling back to urllib: {exc}")
    download_file_with_detected_proxy(url=url, destination=destination)


def _curl_available() -> bool:
    return shutil.which("curl") is not None


def _download_with_curl(*, url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"{destination.name}.",
        suffix=".download",
        dir=destination.parent,
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
    command = [
        "curl",
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--output",
        str(temp_path),
        url,
    ]
    try:
        subprocess.run(command, check=True, env=os.environ.copy())  # noqa: S603
        temp_path.replace(destination)
    except (OSError, subprocess.CalledProcessError) as exc:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"url={url} error={exc}") from exc


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


def write_launcher(*, runtime_root: Path, runtime_python: Path) -> Path:
    launcher_path = runtime_root / "bin" / "munk"
    runtime_python_rel = os.path.relpath(runtime_python, launcher_path.parent)
    launcher_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'SOURCE_PATH="${BASH_SOURCE[0]}"',
                'while [[ -L "$SOURCE_PATH" ]]; do',
                '  SOURCE_DIR="$(cd "$(dirname "$SOURCE_PATH")" && pwd)"',
                '  LINK_TARGET="$(readlink "$SOURCE_PATH")"',
                '  if [[ "$LINK_TARGET" != /* ]]; then',
                '    SOURCE_PATH="$SOURCE_DIR/$LINK_TARGET"',
                "  else",
                '    SOURCE_PATH="$LINK_TARGET"',
                "  fi",
                "done",
                'SCRIPT_DIR="$(cd "$(dirname "$SOURCE_PATH")" && pwd)"',
                'RUNTIME_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"',
                'export MUNK_RUNTIME_ROOT="$RUNTIME_ROOT"',
                f'exec "$SCRIPT_DIR/{runtime_python_rel}" -m munk.cli "$@"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    launcher_path.chmod(0o755)
    return launcher_path


def ensure_uv_available() -> str:
    uv_bin = shutil.which("uv")
    if uv_bin is None:
        raise RuntimeError("missing 'uv' executable; install uv before running standalone runtime scripts")
    return uv_bin


def ensure_pnpm_available() -> str:
    pnpm_bin = shutil.which("pnpm")
    if pnpm_bin is None:
        raise RuntimeError("missing 'pnpm' executable; install pnpm before preparing recording runtime assets")
    return pnpm_bin


def node_distribution_target() -> str:
    machine = normalized_arch()
    if machine == "arm64":
        return "darwin-arm64"
    if machine == "x86_64":
        return "darwin-x64"
    raise RuntimeError(f"unsupported macOS architecture for bundled node runtime: {machine}")


def build_pinned_node_distribution_url() -> str:
    asset_name = f"node-{NODE_RUNTIME_VERSION}-{node_distribution_target()}.tar.gz"
    return f"https://nodejs.org/dist/{NODE_RUNTIME_VERSION}/{asset_name}"


def resolve_node_distribution_archive(*, download_dir: Path) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    url = build_pinned_node_distribution_url()
    destination = download_dir / Path(url).name
    if not destination.exists():
        print(f"downloading bundled node runtime: {url}")
        download_file_with_detected_proxy(url=url, destination=destination)
    return destination


def install_bundled_node_runtime(*, runtime_root: Path, download_dir: Path) -> None:
    runtime_paths = resolve_recording_runtime_asset_paths(runtime_root=runtime_root)
    archive_path = resolve_node_distribution_archive(download_dir=download_dir)
    if runtime_paths.node_dir.exists():
        shutil.rmtree(runtime_paths.node_dir)
    runtime_paths.node_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="munk-node-runtime-") as temp_dir:
        temp_path = Path(temp_dir)
        with tarfile.open(archive_path, mode="r:gz") as archive:
            archive.extractall(temp_path)
        extracted = normalize_extracted_root(temp_path)
        for child in extracted.iterdir():
            shutil.move(str(child), str(runtime_paths.node_dir / child.name))
    runtime_paths.node_bin.chmod(0o755)
    runtime_paths.node_version_marker.write_text(f"{NODE_RUNTIME_VERSION}\n", encoding="utf-8")


def resolve_recording_source_asset_paths(*, project_root: Path) -> RecordingSourceAssetPaths:
    workspace_root = project_root.resolve()
    recording_web_dir = workspace_root / "apps" / "web-ui"
    recording_bridge_dir = workspace_root / "sidecars" / "recording-bridge-local"
    return RecordingSourceAssetPaths(
        workspace_root=workspace_root,
        workspace_package_json=workspace_root / "package.json",
        workspace_lockfile=workspace_root / "pnpm-lock.yaml",
        workspace_manifest=workspace_root / "pnpm-workspace.yaml",
        workspace_node_modules=workspace_root / "node_modules",
        workspace_pnpm_store=workspace_root / "node_modules" / ".pnpm",
        recording_web_dir=recording_web_dir,
        recording_web_dist=recording_web_dir / "dist",
        recording_bridge_dir=recording_bridge_dir,
        recording_bridge_dist=recording_bridge_dir / "dist",
        recording_bridge_node_modules=recording_bridge_dir / "node_modules",
        recording_bridge_package_json=recording_bridge_dir / "package.json",
        recording_bridge_server_bin=(
            recording_bridge_dir / "node_modules" / "@yume-chan" / "fetch-scrcpy-server" / "server.bin"
        ),
    )


def resolve_recording_runtime_asset_paths(*, runtime_root: Path) -> RecordingRuntimeAssetPaths:
    node_dir = runtime_root / "sidecars" / "node"
    return RecordingRuntimeAssetPaths(
        recording_ui_dir=runtime_root / "resources" / "core" / "recording-ui",
        recording_bridge_dir=runtime_root / "sidecars" / "recording-bridge",
        sidecars_node_modules_dir=runtime_root / "sidecars" / "node_modules",
        sidecars_pnpm_store=runtime_root / "sidecars" / "node_modules" / ".pnpm",
        node_dir=node_dir,
        node_bin=node_dir / "bin" / "node",
        node_version_marker=node_dir / NODE_RUNTIME_VERSION_MARKER_FILE,
    )


def recording_asset_fingerprint(*, project_root: Path) -> str:
    paths = resolve_recording_source_asset_paths(project_root=project_root)
    fingerprint_sources = [
        paths.workspace_package_json,
        paths.workspace_lockfile,
        paths.workspace_manifest,
        paths.recording_web_dir / "package.json",
        paths.recording_web_dir / "index.html",
        paths.recording_web_dir / "src",
        paths.recording_web_dir / "public",
        paths.recording_web_dir / "vite.config.ts",
        paths.recording_web_dir / "tsconfig.app.json",
        paths.recording_web_dir / "tsconfig.json",
        paths.recording_web_dir / "tsconfig.node.json",
        paths.recording_bridge_package_json,
        paths.recording_bridge_dir / "src",
        paths.recording_bridge_dir / "test",
        paths.recording_bridge_dir / "tsconfig.json",
    ]
    return fingerprint_paths(fingerprint_sources)


def recording_source_assets_ready(*, project_root: Path) -> bool:
    paths = resolve_recording_source_asset_paths(project_root=project_root)
    return (
        paths.workspace_package_json.exists()
        and paths.workspace_lockfile.exists()
        and paths.workspace_manifest.exists()
        and paths.recording_bridge_package_json.exists()
        and paths.workspace_node_modules.exists()
        and paths.workspace_pnpm_store.exists()
        and paths.recording_web_dist.exists()
        and paths.recording_bridge_dist.exists()
        and paths.recording_bridge_node_modules.exists()
        and paths.recording_bridge_server_bin.exists()
    )


def recording_runtime_assets_present(*, runtime_root: Path) -> bool:
    runtime_paths = resolve_recording_runtime_asset_paths(runtime_root=runtime_root)
    return (
        (runtime_paths.recording_ui_dir / "index.html").exists()
        and (runtime_paths.recording_bridge_dir / "dist" / "app.js").exists()
        and (runtime_paths.recording_bridge_dir / "dist" / "standalone_bootstrap.js").exists()
        and (runtime_paths.recording_bridge_dir / "node_modules").exists()
        and (runtime_paths.recording_bridge_dir / "node_modules" / "fastify-cli" / "cli.js").exists()
        and (
            runtime_paths.recording_bridge_dir
            / "node_modules"
            / "@yume-chan"
            / "fetch-scrcpy-server"
            / "server.bin"
        ).exists()
        and runtime_paths.sidecars_pnpm_store.exists()
        and (runtime_paths.recording_bridge_dir / "package.json").exists()
        and runtime_paths.node_bin.exists()
        and runtime_paths.node_version_marker.exists()
        and runtime_paths.node_version_marker.read_text(encoding="utf-8").strip() == NODE_RUNTIME_VERSION
    )


def recording_runtime_asset_relpaths(*, runtime_root: Path) -> dict[str, str]:
    runtime_paths = resolve_recording_runtime_asset_paths(runtime_root=runtime_root)
    if not recording_runtime_assets_present(runtime_root=runtime_root):
        raise RuntimeError(f"recording runtime assets are missing under: {runtime_root}")
    return {
        "recording_ui_relpath": os.path.relpath(runtime_paths.recording_ui_dir, runtime_root),
        "recording_bridge_relpath": os.path.relpath(runtime_paths.recording_bridge_dir, runtime_root),
        "node_relpath": os.path.relpath(runtime_paths.node_bin, runtime_root),
    }


def prepare_recording_source_assets(*, project_root: Path, force: bool = False, cwd: Path | None = None) -> None:
    paths = resolve_recording_source_asset_paths(project_root=project_root)
    if not paths.workspace_package_json.exists():
        raise RuntimeError(f"missing workspace package.json for recording assets: {paths.workspace_package_json}")
    if not paths.workspace_lockfile.exists():
        raise RuntimeError(f"missing pnpm lockfile for recording assets: {paths.workspace_lockfile}")
    if not paths.workspace_manifest.exists():
        raise RuntimeError(f"missing pnpm workspace manifest for recording assets: {paths.workspace_manifest}")
    if not paths.recording_bridge_package_json.exists():
        raise RuntimeError(
            f"missing recording bridge package.json for recording assets: {paths.recording_bridge_package_json}"
        )
    pnpm_bin = ensure_pnpm_available()
    workdir = cwd or paths.workspace_root
    install_required = (
        force
        or not paths.workspace_node_modules.exists()
        or not paths.recording_bridge_node_modules.exists()
    )
    if install_required:
        run_command([pnpm_bin, "install", "--frozen-lockfile"], cwd=workdir)
    build_required = force or not paths.recording_web_dist.exists() or not paths.recording_bridge_dist.exists()
    if build_required:
        run_command([pnpm_bin, "-r", "build"], cwd=workdir)
    fetch_required = force or not paths.recording_bridge_server_bin.exists()
    if fetch_required:
        ensure_scrcpy_server_binary(
            destination=paths.recording_bridge_server_bin,
            pnpm_bin=pnpm_bin,
            recording_bridge_dir=paths.recording_bridge_dir,
            cwd=workdir,
        )


def ensure_scrcpy_server_binary(
    *,
    destination: Path,
    pnpm_bin: str,
    recording_bridge_dir: Path,
    cwd: Path,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        download_file_with_detected_proxy(
            url=SCRCPY_SERVER_RELEASE_URL,
            destination=destination,
        )
        return
    except RuntimeError as exc:
        print(f"warning: python download failed for scrcpy-server, falling back to node fetch: {exc}")
    run_command(
        [pnpm_bin, "--dir", str(recording_bridge_dir), "exec", "fetch-scrcpy-server", SCRCPY_SERVER_VERSION],
        cwd=cwd,
    )


def download_file_with_detected_proxy(*, url: str, destination: Path) -> None:
    proxies = urllib.request.getproxies_environment()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "munk-runtime-builder/1.0"},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f"{destination.name}.",
        suffix=".download",
        dir=destination.parent,
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        with opener.open(request) as response, temp_path.open("wb") as handle:  # noqa: S310
            shutil.copyfileobj(response, handle)
        temp_path.replace(destination)
    except (urllib.error.URLError, OSError) as exc:
        temp_path.unlink(missing_ok=True)
        proxy_summary = _format_proxy_summary(proxies)
        raise RuntimeError(f"url={url} proxies={proxy_summary} error={exc}") from exc


def _format_proxy_summary(proxies: dict[str, str]) -> str:
    if not proxies:
        return "none"
    return ",".join(f"{scheme}={value}" for scheme, value in sorted(proxies.items()))


def copy_recording_runtime_assets(*, project_root: Path, runtime_root: Path, download_dir: Path) -> dict[str, str]:
    source_paths = resolve_recording_source_asset_paths(project_root=project_root)
    if not recording_source_assets_ready(project_root=project_root):
        raise RuntimeError(
            "recording source assets are not ready; run prepare_recording_source_assets() before copying them "
            f"from {project_root}"
        )
    runtime_paths = resolve_recording_runtime_asset_paths(runtime_root=runtime_root)
    if runtime_paths.recording_ui_dir.exists():
        shutil.rmtree(runtime_paths.recording_ui_dir)
    shutil.copytree(source_paths.recording_web_dist, runtime_paths.recording_ui_dir)
    if runtime_paths.recording_bridge_dir.exists():
        shutil.rmtree(runtime_paths.recording_bridge_dir)
    if runtime_paths.sidecars_node_modules_dir.exists():
        shutil.rmtree(runtime_paths.sidecars_node_modules_dir)
    runtime_paths.recording_bridge_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_paths.recording_bridge_dist, runtime_paths.recording_bridge_dir / "dist")
    runtime_paths.sidecars_pnpm_store.parent.mkdir(parents=True, exist_ok=True)
    # recording-bridge-local is installed via pnpm workspace symlinks. The bridge-local node_modules
    # entries resolve into the workspace .pnpm store, so the runtime must copy both the symlink surface
    # and the underlying store to keep transitive dependencies resolvable after relocation.
    shutil.copytree(
        source_paths.workspace_pnpm_store,
        runtime_paths.sidecars_pnpm_store,
        symlinks=True,
    )
    shutil.copytree(
        source_paths.recording_bridge_node_modules,
        runtime_paths.recording_bridge_dir / "node_modules",
        symlinks=True,
    )
    shutil.copy2(source_paths.recording_bridge_package_json, runtime_paths.recording_bridge_dir / "package.json")
    _rewrite_runtime_bridge_node_module_symlinks(
        source_node_modules=source_paths.recording_bridge_node_modules,
        runtime_node_modules=runtime_paths.recording_bridge_dir / "node_modules",
        source_pnpm_store=source_paths.workspace_pnpm_store,
        runtime_pnpm_store=runtime_paths.sidecars_pnpm_store,
    )
    install_bundled_node_runtime(runtime_root=runtime_root, download_dir=download_dir)
    return recording_runtime_asset_relpaths(runtime_root=runtime_root)


def _rewrite_runtime_bridge_node_module_symlinks(
    *,
    source_node_modules: Path,
    runtime_node_modules: Path,
    source_pnpm_store: Path,
    runtime_pnpm_store: Path,
) -> None:
    source_pnpm_store_resolved = source_pnpm_store.resolve()
    for runtime_link in runtime_node_modules.rglob("*"):
        if not runtime_link.is_symlink():
            continue
        source_link = source_node_modules / runtime_link.relative_to(runtime_node_modules)
        if not source_link.is_symlink():
            continue
        source_target = source_link.resolve()
        try:
            relpath_in_store = source_target.relative_to(source_pnpm_store_resolved)
        except ValueError:
            continue
        runtime_target = runtime_pnpm_store / relpath_in_store
        runtime_link.unlink()
        runtime_link.symlink_to(Path(os.path.relpath(runtime_target, start=runtime_link.parent)))


def clean_project_build_artifacts(project_dir: Path, *, preserve_paths: list[Path] | None = None) -> None:
    preserved = [path.resolve() for path in (preserve_paths or [])]
    for candidate in [project_dir / "build", project_dir / "dist"]:
        if not candidate.exists():
            continue
        resolved_candidate = candidate.resolve()
        if any(path == resolved_candidate or resolved_candidate in path.parents for path in preserved):
            continue
        shutil.rmtree(candidate)
    src_dir = project_dir / "src"
    if not src_dir.exists():
        return
    for egg_info_dir in src_dir.glob("*.egg-info"):
        if egg_info_dir.is_dir():
            shutil.rmtree(egg_info_dir)
    for pattern in ("**/*.so", "**/*.pyd"):
        for compiled_path in src_dir.glob(pattern):
            compiled_path.unlink(missing_ok=True)


def verify_bundled_node_runtime(
    *,
    runtime_root: Path,
    forbidden_prefixes: tuple[str, ...] = ("/opt/homebrew/", "/usr/local/opt/"),
) -> None:
    runtime_paths = resolve_recording_runtime_asset_paths(runtime_root=runtime_root)
    if not runtime_paths.node_bin.exists():
        raise RuntimeError(f"bundled node runtime is missing: {runtime_paths.node_bin}")
    completed = subprocess.run(  # noqa: S603
        ["otool", "-L", str(runtime_paths.node_bin)],
        cwd=runtime_root,
        check=False,
        capture_output=True,
        text=True,
    )
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip()).strip()
    if completed.returncode != 0:
        raise RuntimeError(
            "failed to inspect bundled node runtime dependencies.\n"
            f"command: otool -L {runtime_paths.node_bin}\n"
            f"output:\n{output or '<empty>'}"
        )
    dependency_lines = [
        line.strip()
        for line in output.splitlines()[1:]
        if line.strip()
    ]
    offending_lines = [
        line
        for line in dependency_lines
        if any(prefix in line for prefix in forbidden_prefixes)
    ]
    if offending_lines:
        forbidden_summary = ", ".join(forbidden_prefixes)
        offending_summary = "\n".join(offending_lines)
        raise RuntimeError(
            "bundled node runtime references external machine-specific libraries.\n"
            f"forbidden prefixes: {forbidden_summary}\n"
            f"node: {runtime_paths.node_bin}\n"
            f"offending lines:\n{offending_summary}"
        )


def check_uv_lock(*, uv_bin: str, project_dir: Path, cwd: Path) -> None:
    lock_path = project_dir / "uv.lock"
    if not lock_path.exists():
        raise RuntimeError(f"missing uv.lock for {project_dir}; run `python scripts/update_uv_locks.py` first")
    completed = subprocess.run(  # noqa: S603
        [uv_bin, "lock", "--project", str(project_dir), "--check"],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(
            f"uv.lock is out of date for {project_dir}; run `python scripts/update_uv_locks.py` first.\n{stderr}"
        )


def sync_project_dependencies(
    *,
    uv_bin: str,
    project_dir: Path,
    runtime_python: Path,
    cwd: Path,
) -> None:
    check_uv_lock(uv_bin=uv_bin, project_dir=project_dir, cwd=cwd)
    with tempfile.NamedTemporaryFile(
        prefix=f"{project_dir.name}-locked-", suffix=".txt", delete=False
    ) as requirements_file:
        requirements_path = Path(requirements_file.name)
    try:
        run_command(
            [
                uv_bin,
                "export",
                "--project",
                str(project_dir),
                "--format",
                "requirements.txt",
                "--locked",
                "--no-header",
                "--no-annotate",
                "--no-emit-project",
                "--no-emit-local",
                "--output-file",
                str(requirements_path),
            ],
            cwd=cwd,
        )
        run_command(
            [
                uv_bin,
                "pip",
                "install",
                "--python",
                str(runtime_python),
                "-r",
                str(requirements_path),
            ],
            cwd=cwd,
        )
    finally:
        requirements_path.unlink(missing_ok=True)


def install_editable_project(
    *,
    uv_bin: str,
    runtime_python: Path,
    project_dir: Path,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> None:
    run_command(
        [
            uv_bin,
            "pip",
            "install",
            "--python",
            str(runtime_python),
            "--no-deps",
            "-e",
            str(project_dir),
        ],
        cwd=cwd,
        env=env,
    )


def install_wheel_files(*, uv_bin: str, runtime_python: Path, wheel_paths: list[Path], cwd: Path) -> None:
    if not wheel_paths:
        raise RuntimeError("no wheel files provided for installation")
    run_command(
        [
            uv_bin,
            "pip",
            "install",
            "--python",
            str(runtime_python),
            "--no-deps",
            *[str(path) for path in wheel_paths],
        ],
        cwd=cwd,
    )


def run_uv_pip_check(*, uv_bin: str, runtime_python: Path, cwd: Path) -> None:
    run_command(
        [
            uv_bin,
            "pip",
            "check",
            "--python",
            str(runtime_python),
        ],
        cwd=cwd,
    )


def default_state_path(*, project_root: Path, kind: str, runtime_root: Path) -> Path:
    return project_root / "dist" / "runtime-build" / f"{kind}-{runtime_root.name}-state.json"


def load_state(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return {str(key): str(value) for key, value in payload.items()}


def write_state(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fingerprint_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    seen: set[Path] = set()
    for path in sorted({path.resolve() for path in paths}):
        if path in seen:
            continue
        seen.add(path)
        if not path.exists():
            digest.update(f"missing:{path}".encode("utf-8"))
            continue
        if path.is_file():
            if _should_ignore_fingerprint_path(path):
                continue
            _update_digest_for_file(digest, path)
            continue
        digest.update(f"dir:{path}".encode("utf-8"))
        for child in sorted(path.rglob("*")):
            if _should_ignore_fingerprint_path(child):
                continue
            if child.is_dir():
                digest.update(f"subdir:{child.relative_to(path)}".encode("utf-8"))
                continue
            _update_digest_for_file(digest, child, relative_to=path)
    return digest.hexdigest()


def run_command(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, cwd=cwd, env=env)


def _should_ignore_fingerprint_path(path: Path) -> bool:
    ignored_names = {"__pycache__", ".pytest_cache", ".ruff_cache", ".venv", ".DS_Store"}
    if any(part in ignored_names for part in path.parts):
        return True
    if any(part.endswith(".egg-info") for part in path.parts):
        return True
    return path.suffix in {".pyc", ".pyo"}


def _update_digest_for_file(digest: hashlib._Hash, path: Path, *, relative_to: Path | None = None) -> None:
    stat = path.stat()
    label = str(path.relative_to(relative_to)) if relative_to is not None else str(path)
    digest.update(
        f"file:{label}:{stat.st_size}:{stat.st_mtime_ns}".encode("utf-8")
    )
