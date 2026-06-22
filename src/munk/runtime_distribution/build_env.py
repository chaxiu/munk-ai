from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import munk.runtime_distribution.build_env_android as _build_env_android
import munk.runtime_distribution.build_env_assets as _build_env_assets
import munk.runtime_distribution.build_env_ios_bridge as _build_env_ios_bridge
import munk.runtime_distribution.build_env_knowledge as _build_env_knowledge
from munk.runtime_distribution.build_env_android import (
    ADB_VERSION_MARKER_FILE,
    AndroidPlatformToolsPin,
    extract_android_platform_tools_archive,
    load_android_platform_tools_pin,
    load_android_platform_tools_version,
    verify_android_platform_tools_archive,
    verify_android_platform_tools_installation,
)
from munk.runtime_distribution.build_env_android import (
    copy_adb_sidecar as _copy_adb_sidecar_impl,
)
from munk.runtime_distribution.build_env_android import (
    install_android_platform_tools as _install_android_platform_tools_impl,
)
from munk.runtime_distribution.build_env_assets import (
    NODE_RUNTIME_VERSION,
    NODE_RUNTIME_VERSION_MARKER_FILE,
    RecordingRuntimeAssetPaths,
    RecordingSourceAssetPaths,
    ensure_pnpm_available,
    recording_asset_fingerprint,
    recording_bridge_fingerprint,
    recording_dependency_fingerprint,
    recording_runtime_asset_relpaths,
    recording_runtime_assets_present,
    recording_source_assets_ready,
    recording_web_fingerprint,
    resolve_node_distribution_archive,
    resolve_recording_runtime_asset_paths,
    resolve_recording_source_asset_paths,
)
from munk.runtime_distribution.build_env_assets import (
    copy_recording_runtime_assets as _copy_recording_runtime_assets_impl,
)
from munk.runtime_distribution.build_env_assets import (
    ensure_scrcpy_server_binary as _ensure_scrcpy_server_binary_impl,
)
from munk.runtime_distribution.build_env_assets import (
    install_bundled_node_runtime as _install_bundled_node_runtime_impl,
)
from munk.runtime_distribution.build_env_assets import (
    prepare_recording_source_assets as _prepare_recording_source_assets_impl,
)
from munk.runtime_distribution.build_env_downloads import (
    download_file_with_detected_proxy as _download_file_with_detected_proxy_impl,
)
from munk.runtime_distribution.build_env_downloads import (
    download_with_proxy_support as _download_with_proxy_support_impl,
)
from munk.runtime_distribution.build_env_downloads import (
    extract_archive,
)
from munk.runtime_distribution.build_env_downloads import (
    load_json_with_detected_proxy as _load_json_with_detected_proxy_impl,
)
from munk.runtime_distribution.build_env_ios_bridge import (
    IOSBridgeRuntimeAssetPaths,
    IOSBridgeSourceAssetPaths,
    ios_bridge_asset_fingerprint,
    ios_bridge_runtime_asset_relpaths,
    ios_bridge_runtime_assets_present,
    ios_bridge_source_assets_ready,
    resolve_ios_bridge_runtime_asset_paths,
    resolve_ios_bridge_source_asset_paths,
)
from munk.runtime_distribution.build_env_ios_bridge import (
    copy_ios_bridge_runtime_assets as _copy_ios_bridge_runtime_assets_impl,
)
from munk.runtime_distribution.build_env_ios_bridge import (
    prepare_ios_bridge_source_assets as _prepare_ios_bridge_source_assets_impl,
)
from munk.runtime_distribution.build_env_knowledge import (
    KNOWLEDGE_EMBED_MODEL_CONFIG_KEY,
    KNOWLEDGE_EMBED_MODEL_MARKER_FILE,
    KNOWLEDGE_EMBED_MODEL_ONNX_RELPATH,
    KNOWLEDGE_EMBED_MODEL_PROJECT_RELPATH,
    KnowledgeEmbedModelRelease,
)
from munk.runtime_distribution.build_env_knowledge import (
    load_knowledge_embed_model_release as _load_knowledge_embed_model_release_impl,
)
from munk.runtime_distribution.build_env_knowledge import (
    prepare_knowledge_embed_model as _prepare_knowledge_embed_model_impl,
)
from munk.runtime_distribution.build_env_platform import (
    RuntimeBuildTarget,
    build_android_platform_tools_url,
    ensure_supported_platform,
    normalized_arch,
    normalized_platform,
    pbs_target_triple,
    resolve_android_platform_tools_target_platform,
    resolve_expected_adb_path,
    resolve_host_target,
)
from munk.runtime_distribution.build_env_state import (
    default_state_path,
    fingerprint_paths,
    load_state,
    run_command,
    write_state,
)

download_with_proxy_support = _download_with_proxy_support_impl
download_file_with_detected_proxy = _download_file_with_detected_proxy_impl
_load_json_with_detected_proxy = _load_json_with_detected_proxy_impl
install_bundled_node_runtime = _install_bundled_node_runtime_impl


@dataclass(frozen=True)
class RuntimeVersionDefaults:
    release_tag: str
    python_version: str
    archive_flavor: str


@dataclass(frozen=True)
class DependencyProject:
    name: str
    project_dir: Path


def load_runtime_version_defaults(config_path: Path) -> RuntimeVersionDefaults:
    payload_obj = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload_obj, dict):
        raise RuntimeError(f"invalid runtime version config: expected object in {config_path}")
    payload_dict = cast(dict[str, object], payload_obj)
    pbs = payload_dict.get("python_build_standalone")
    if not isinstance(pbs, dict):
        raise RuntimeError(f"invalid runtime version config: missing 'python_build_standalone' in {config_path}")
    pbs_dict = cast(dict[str, object], pbs)
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


def build_pinned_pbs_url(
    *,
    defaults: RuntimeVersionDefaults,
    platform_name: str | None = None,
    arch: str | None = None,
) -> str:
    asset_name = (
        f"cpython-{defaults.python_version}+{defaults.release_tag}-"
        f"{pbs_target_triple(platform_name=platform_name, arch=arch)}-{defaults.archive_flavor}.tar.gz"
    )
    return (
        "https://github.com/astral-sh/python-build-standalone/releases/download/"
        f"{defaults.release_tag}/{asset_name}"
    )


def resolve_pbs_archive(
    *,
    download_dir: Path,
    defaults: RuntimeVersionDefaults,
    platform_name: str | None = None,
    arch: str | None = None,
) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    url = build_pinned_pbs_url(defaults=defaults, platform_name=platform_name, arch=arch)
    destination = download_dir / Path(url).name
    if not destination.exists():
        print(f"downloading python-build-standalone: {url}")
        urllib.request.urlretrieve(url, destination)  # noqa: S310
    return destination


def extract_pbs_archive(*, archive_path: Path, python_root: Path, cwd: Path) -> None:
    _ = cwd
    extract_archive(
        archive_path=archive_path,
        destination_dir=python_root,
        temp_prefix="munk-pbs-extract-",
        error_prefix="PBS",
    )


def find_runtime_python(python_root: Path) -> Path:
    for candidate in [
        python_root / "python.exe",
        python_root / "bin" / "python3",
        python_root / "bin" / "python",
    ]:
        if candidate.exists():
            return candidate
    raise RuntimeError(f"could not find runtime python under {python_root}")


def write_launcher(*, runtime_root: Path, runtime_python: Path) -> Path:
    is_windows_runtime = runtime_python.suffix.lower() == ".exe"
    launcher_path = runtime_root / "bin" / ("munk.cmd" if is_windows_runtime else "munk")
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_python_rel = os.path.relpath(runtime_python, launcher_path.parent)
    if is_windows_runtime:
        launcher_path.write_text(
            "\r\n".join(
                [
                    "@echo off",
                    "setlocal",
                    'set "SCRIPT_DIR=%~dp0"',
                    'for %%I in ("%SCRIPT_DIR%..") do set "RUNTIME_ROOT=%%~fI"',
                    'set "MUNK_RUNTIME_ROOT=%RUNTIME_ROOT%"',
                    f'"%SCRIPT_DIR%{runtime_python_rel}" -m munk.cli %*',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return launcher_path
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


def install_android_platform_tools(
    *,
    pin: AndroidPlatformToolsPin,
    target_platform: str,
    download_dir: Path,
    destination_root: Path,
    force: bool = False,
) -> Path:
    _build_env_android.download_with_proxy_support = download_with_proxy_support
    _build_env_android.extract_android_platform_tools_archive = extract_android_platform_tools_archive
    return _install_android_platform_tools_impl(
        pin=pin,
        target_platform=target_platform,
        download_dir=download_dir,
        destination_root=destination_root,
        force=force,
    )


def copy_adb_sidecar(
    *,
    project_root: Path,
    runtime_root: Path,
    download_dir: Path,
    pin: AndroidPlatformToolsPin,
    target_platform: str = "auto",
) -> Path:
    _build_env_android.install_android_platform_tools = install_android_platform_tools
    _build_env_android.resolve_android_platform_tools_target_platform = resolve_android_platform_tools_target_platform
    return _copy_adb_sidecar_impl(
        project_root=project_root,
        runtime_root=runtime_root,
        download_dir=download_dir,
        pin=pin,
        target_platform=target_platform,
    )


def load_knowledge_embed_model_release(*, config_path: Path) -> KnowledgeEmbedModelRelease:
    _build_env_knowledge.load_json_with_detected_proxy = _load_json_with_detected_proxy
    return _load_knowledge_embed_model_release_impl(config_path=config_path)


def prepare_knowledge_embed_model(
    *,
    project_root: Path,
    download_dir: Path,
    version_config_path: Path,
    force: bool = False,
) -> Path:
    _build_env_knowledge.download_with_proxy_support = download_with_proxy_support
    _build_env_knowledge.load_json_with_detected_proxy = _load_json_with_detected_proxy
    return _prepare_knowledge_embed_model_impl(
        project_root=project_root,
        download_dir=download_dir,
        version_config_path=version_config_path,
        force=force,
    )


def ensure_scrcpy_server_binary(
    *,
    destination: Path,
    pnpm_bin: str,
    recording_bridge_dir: Path,
    cwd: Path,
) -> None:
    _build_env_assets.download_file_with_detected_proxy = download_file_with_detected_proxy
    _build_env_assets.run_command = run_command
    _ensure_scrcpy_server_binary_impl(
        destination=destination,
        pnpm_bin=pnpm_bin,
        recording_bridge_dir=recording_bridge_dir,
        cwd=cwd,
    )


def prepare_recording_source_assets(
    *,
    project_root: Path,
    force: bool = False,
    install: bool = False,
    build_web: bool = False,
    build_bridge: bool = False,
    fetch_scrcpy: bool = False,
    cwd: Path | None = None,
) -> None:
    _build_env_assets.ensure_pnpm_available = ensure_pnpm_available
    _build_env_assets.ensure_scrcpy_server_binary = ensure_scrcpy_server_binary
    _build_env_assets.run_command = run_command
    _prepare_recording_source_assets_impl(
        project_root=project_root,
        force=force,
        install=install,
        build_web=build_web,
        build_bridge=build_bridge,
        fetch_scrcpy=fetch_scrcpy,
        cwd=cwd,
    )


def copy_recording_runtime_assets(*, project_root: Path, runtime_root: Path, download_dir: Path) -> dict[str, str]:
    _build_env_assets.install_bundled_node_runtime = install_bundled_node_runtime
    return _copy_recording_runtime_assets_impl(
        project_root=project_root,
        runtime_root=runtime_root,
        download_dir=download_dir,
    )


def prepare_ios_bridge_source_assets(*, project_root: Path, force: bool = False, cwd: Path | None = None) -> None:
    _build_env_ios_bridge.ensure_pnpm_available = ensure_pnpm_available
    _build_env_ios_bridge.run_command = run_command
    _prepare_ios_bridge_source_assets_impl(project_root=project_root, force=force, cwd=cwd)


def copy_ios_bridge_runtime_assets(*, project_root: Path, runtime_root: Path, download_dir: Path) -> dict[str, str]:
    _build_env_ios_bridge.install_bundled_node_runtime = install_bundled_node_runtime
    return _copy_ios_bridge_runtime_assets_impl(
        project_root=project_root,
        runtime_root=runtime_root,
        download_dir=download_dir,
    )


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


__all__ = [
    "ADB_VERSION_MARKER_FILE",
    "AndroidPlatformToolsPin",
    "DependencyProject",
    "IOSBridgeRuntimeAssetPaths",
    "IOSBridgeSourceAssetPaths",
    "KNOWLEDGE_EMBED_MODEL_CONFIG_KEY",
    "KNOWLEDGE_EMBED_MODEL_MARKER_FILE",
    "KNOWLEDGE_EMBED_MODEL_ONNX_RELPATH",
    "KNOWLEDGE_EMBED_MODEL_PROJECT_RELPATH",
    "KnowledgeEmbedModelRelease",
    "NODE_RUNTIME_VERSION",
    "NODE_RUNTIME_VERSION_MARKER_FILE",
    "RecordingRuntimeAssetPaths",
    "RecordingSourceAssetPaths",
    "RuntimeBuildTarget",
    "RuntimeVersionDefaults",
    "build_android_platform_tools_url",
    "build_pinned_pbs_url",
    "check_uv_lock",
    "clean_project_build_artifacts",
    "copy_adb_sidecar",
    "copy_ios_bridge_runtime_assets",
    "copy_recording_runtime_assets",
    "default_state_path",
    "ensure_pnpm_available",
    "ensure_scrcpy_server_binary",
    "ensure_supported_platform",
    "ensure_uv_available",
    "extract_android_platform_tools_archive",
    "extract_pbs_archive",
    "find_runtime_python",
    "fingerprint_paths",
    "install_android_platform_tools",
    "install_editable_project",
    "install_wheel_files",
    "ios_bridge_asset_fingerprint",
    "ios_bridge_runtime_asset_relpaths",
    "ios_bridge_runtime_assets_present",
    "ios_bridge_source_assets_ready",
    "load_android_platform_tools_pin",
    "load_android_platform_tools_version",
    "load_knowledge_embed_model_release",
    "load_runtime_version_defaults",
    "load_state",
    "normalized_arch",
    "normalized_platform",
    "pbs_target_triple",
    "prepare_ios_bridge_source_assets",
    "prepare_knowledge_embed_model",
    "prepare_recording_source_assets",
    "recording_asset_fingerprint",
    "recording_bridge_fingerprint",
    "recording_dependency_fingerprint",
    "recording_runtime_asset_relpaths",
    "recording_runtime_assets_present",
    "recording_source_assets_ready",
    "recording_web_fingerprint",
    "resolve_android_platform_tools_target_platform",
    "resolve_expected_adb_path",
    "resolve_host_target",
    "resolve_ios_bridge_runtime_asset_paths",
    "resolve_ios_bridge_source_asset_paths",
    "resolve_node_distribution_archive",
    "resolve_pbs_archive",
    "resolve_recording_runtime_asset_paths",
    "resolve_recording_source_asset_paths",
    "run_command",
    "run_uv_pip_check",
    "sync_project_dependencies",
    "verify_android_platform_tools_archive",
    "verify_android_platform_tools_installation",
    "verify_bundled_node_runtime",
    "write_launcher",
    "write_state",
]
