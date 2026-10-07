from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from munk.runtime_distribution.build_env_downloads import download_file_with_detected_proxy, extract_archive
from munk.runtime_distribution.build_env_platform import (
    build_pinned_node_distribution_url,
    normalized_platform,
    resolve_host_target,
)
from munk.runtime_distribution.build_env_state import fingerprint_paths, run_command

SCRCPY_SERVER_VERSION = "3.3.3"
SCRCPY_SERVER_RELEASE_URL = (
    f"https://github.com/Genymobile/scrcpy/releases/download/v{SCRCPY_SERVER_VERSION}/"
    f"scrcpy-server-v{SCRCPY_SERVER_VERSION}"
)
NODE_RUNTIME_VERSION = "v24.4.1"
NODE_RUNTIME_VERSION_MARKER_FILE = ".munk-node-runtime-version"


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


def ensure_pnpm_available() -> str:
    pnpm_bin = shutil.which("pnpm")
    if pnpm_bin is None:
        raise RuntimeError("missing 'pnpm' executable; install pnpm before preparing recording runtime assets")
    return pnpm_bin


def resolve_node_distribution_archive(
    *,
    download_dir: Path,
    platform_name: str | None = None,
    arch: str | None = None,
) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    url = build_pinned_node_distribution_url(
        node_runtime_version=NODE_RUNTIME_VERSION,
        platform_name=platform_name,
        arch=arch,
    )
    destination = download_dir / Path(url).name
    if not destination.exists():
        print(f"downloading bundled node runtime: {url}")
        download_file_with_detected_proxy(url=url, destination=destination)
    return destination


def install_bundled_node_runtime(*, runtime_root: Path, download_dir: Path) -> None:
    runtime_paths = resolve_recording_runtime_asset_paths(runtime_root=runtime_root)
    target = resolve_host_target()
    archive_path = resolve_node_distribution_archive(
        download_dir=download_dir,
        platform_name=target.platform,
        arch=target.arch,
    )
    extract_archive(
        archive_path=archive_path,
        destination_dir=runtime_paths.node_dir,
        temp_prefix="munk-node-runtime-",
        error_prefix="Node",
    )
    if runtime_paths.node_bin.exists() and target.platform != "windows":
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
    node_bin = node_dir / "node.exe" if normalized_platform() == "windows" else node_dir / "bin" / "node"
    return RecordingRuntimeAssetPaths(
        recording_ui_dir=runtime_root / "resources" / "core" / "recording-ui",
        recording_bridge_dir=runtime_root / "sidecars" / "recording-bridge",
        sidecars_node_modules_dir=runtime_root / "sidecars" / "node_modules",
        sidecars_pnpm_store=runtime_root / "sidecars" / "node_modules" / ".pnpm",
        node_dir=node_dir,
        node_bin=node_bin,
        node_version_marker=node_dir / NODE_RUNTIME_VERSION_MARKER_FILE,
    )


def recording_dependency_fingerprint(*, project_root: Path) -> str:
    paths = resolve_recording_source_asset_paths(project_root=project_root)
    return fingerprint_paths(
        [
            paths.workspace_package_json,
            paths.workspace_lockfile,
            paths.workspace_manifest,
            paths.recording_web_dir / "package.json",
            paths.recording_bridge_package_json,
        ]
    )


def recording_web_fingerprint(*, project_root: Path) -> str:
    paths = resolve_recording_source_asset_paths(project_root=project_root)
    return fingerprint_paths(
        [
            paths.recording_web_dir / "package.json",
            paths.recording_web_dir / "index.html",
            paths.recording_web_dir / "src",
            paths.recording_web_dir / "public",
            paths.recording_web_dir / "vite.config.ts",
            paths.recording_web_dir / "tsconfig.app.json",
            paths.recording_web_dir / "tsconfig.json",
            paths.recording_web_dir / "tsconfig.node.json",
        ]
    )


def recording_bridge_fingerprint(*, project_root: Path) -> str:
    paths = resolve_recording_source_asset_paths(project_root=project_root)
    return fingerprint_paths(
        [
            paths.recording_bridge_package_json,
            paths.recording_bridge_dir / "src",
            paths.recording_bridge_dir / "test",
            paths.recording_bridge_dir / "tsconfig.json",
        ]
    )


def recording_asset_fingerprint(*, project_root: Path) -> str:
    return "|".join(
        (
            recording_dependency_fingerprint(project_root=project_root),
            recording_web_fingerprint(project_root=project_root),
            recording_bridge_fingerprint(project_root=project_root),
        )
    )


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
            runtime_paths.recording_bridge_dir / "node_modules" / "@yume-chan" / "fetch-scrcpy-server" / "server.bin"
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
    paths = resolve_recording_source_asset_paths(project_root=project_root)
    if not paths.workspace_package_json.exists():
        raise RuntimeError(f"missing workspace package.json for recording assets: {paths.workspace_package_json}")
    if not paths.workspace_lockfile.exists():
        raise RuntimeError(f"missing pnpm lockfile for recording assets: {paths.workspace_lockfile}")
    if not paths.workspace_manifest.exists():
        raise RuntimeError(f"missing pnpm workspace manifest for recording assets: {paths.workspace_manifest}")
    if not (paths.recording_web_dir / "package.json").exists():
        raise RuntimeError(f"missing recording web package.json for recording assets: {paths.recording_web_dir / 'package.json'}")
    if not paths.recording_bridge_package_json.exists():
        raise RuntimeError(
            f"missing recording bridge package.json for recording assets: {paths.recording_bridge_package_json}"
        )
    pnpm_bin = ensure_pnpm_available()
    workdir = cwd or paths.workspace_root
    install_required = (
        force
        or install
        or not paths.workspace_node_modules.exists()
        or not paths.recording_bridge_node_modules.exists()
    )
    if install_required:
        run_command([pnpm_bin, "install", "--frozen-lockfile"], cwd=workdir)
    build_web_required = force or install_required or build_web or not paths.recording_web_dist.exists()
    if build_web_required:
        run_command([pnpm_bin, "--dir", str(paths.recording_web_dir), "run", "build"], cwd=workdir)
    build_bridge_required = force or install_required or build_bridge or not paths.recording_bridge_dist.exists()
    if build_bridge_required:
        run_command([pnpm_bin, "--dir", str(paths.recording_bridge_dir), "run", "build"], cwd=workdir)
    fetch_required = force or install_required or fetch_scrcpy or not paths.recording_bridge_server_bin.exists()
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


def copy_recording_runtime_assets(*, project_root: Path, runtime_root: Path, download_dir: Path) -> dict[str, str]:
    source_paths = resolve_recording_source_asset_paths(project_root=project_root)
    if not recording_source_assets_ready(project_root=project_root):
        raise RuntimeError(
            "recording source assets are not ready; run prepare_recording_source_assets() before copying them "
            f"from {project_root}"
        )
    runtime_paths = resolve_recording_runtime_asset_paths(runtime_root=runtime_root)
    preserve_symlinks = normalized_platform() != "windows"
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
    shutil.copytree(source_paths.workspace_pnpm_store, runtime_paths.sidecars_pnpm_store, symlinks=preserve_symlinks)
    shutil.copytree(
        source_paths.recording_bridge_node_modules,
        runtime_paths.recording_bridge_dir / "node_modules",
        symlinks=preserve_symlinks,
    )
    shutil.copy2(source_paths.recording_bridge_package_json, runtime_paths.recording_bridge_dir / "package.json")
    if preserve_symlinks:
        rewrite_runtime_bridge_node_module_symlinks(
            source_node_modules=source_paths.recording_bridge_node_modules,
            runtime_node_modules=runtime_paths.recording_bridge_dir / "node_modules",
            source_pnpm_store=source_paths.workspace_pnpm_store,
            runtime_pnpm_store=runtime_paths.sidecars_pnpm_store,
        )
    install_bundled_node_runtime(runtime_root=runtime_root, download_dir=download_dir)
    return recording_runtime_asset_relpaths(runtime_root=runtime_root)


def rewrite_runtime_bridge_node_module_symlinks(
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
