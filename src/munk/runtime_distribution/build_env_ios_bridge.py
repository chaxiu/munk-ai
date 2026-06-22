from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from munk.runtime_distribution.build_env_assets import (
    NODE_RUNTIME_VERSION,
    NODE_RUNTIME_VERSION_MARKER_FILE,
    ensure_pnpm_available,
    install_bundled_node_runtime,
    rewrite_runtime_bridge_node_module_symlinks,
)
from munk.runtime_distribution.build_env_platform import normalized_platform
from munk.runtime_distribution.build_env_state import fingerprint_paths, run_command


@dataclass(frozen=True)
class IOSBridgeSourceAssetPaths:
    workspace_root: Path
    workspace_package_json: Path
    workspace_lockfile: Path
    workspace_manifest: Path
    workspace_node_modules: Path
    workspace_pnpm_store: Path
    ios_bridge_dir: Path
    ios_bridge_dist: Path
    ios_bridge_node_modules: Path
    ios_bridge_package_json: Path


@dataclass(frozen=True)
class IOSBridgeRuntimeAssetPaths:
    ios_bridge_dir: Path
    sidecars_node_modules_dir: Path
    sidecars_pnpm_store: Path
    node_dir: Path
    node_bin: Path
    node_version_marker: Path


def resolve_ios_bridge_source_asset_paths(*, project_root: Path) -> IOSBridgeSourceAssetPaths:
    workspace_root = project_root.resolve()
    ios_bridge_dir = workspace_root / "sidecars" / "ios-device-bridge"
    return IOSBridgeSourceAssetPaths(
        workspace_root=workspace_root,
        workspace_package_json=workspace_root / "package.json",
        workspace_lockfile=workspace_root / "pnpm-lock.yaml",
        workspace_manifest=workspace_root / "pnpm-workspace.yaml",
        workspace_node_modules=workspace_root / "node_modules",
        workspace_pnpm_store=workspace_root / "node_modules" / ".pnpm",
        ios_bridge_dir=ios_bridge_dir,
        ios_bridge_dist=ios_bridge_dir / "dist",
        ios_bridge_node_modules=ios_bridge_dir / "node_modules",
        ios_bridge_package_json=ios_bridge_dir / "package.json",
    )


def resolve_ios_bridge_runtime_asset_paths(*, runtime_root: Path) -> IOSBridgeRuntimeAssetPaths:
    node_dir = runtime_root / "sidecars" / "node"
    node_bin = node_dir / "node.exe" if normalized_platform() == "windows" else node_dir / "bin" / "node"
    return IOSBridgeRuntimeAssetPaths(
        ios_bridge_dir=runtime_root / "sidecars" / "ios-device-bridge",
        sidecars_node_modules_dir=runtime_root / "sidecars" / "node_modules",
        sidecars_pnpm_store=runtime_root / "sidecars" / "node_modules" / ".pnpm",
        node_dir=node_dir,
        node_bin=node_bin,
        node_version_marker=node_dir / NODE_RUNTIME_VERSION_MARKER_FILE,
    )


def ios_bridge_asset_fingerprint(*, project_root: Path) -> str:
    paths = resolve_ios_bridge_source_asset_paths(project_root=project_root)
    return fingerprint_paths(
        [
            paths.workspace_package_json,
            paths.workspace_lockfile,
            paths.workspace_manifest,
            paths.ios_bridge_package_json,
            paths.ios_bridge_dir / "src",
            paths.ios_bridge_dir / "test",
            paths.ios_bridge_dir / "tsconfig.json",
        ]
    )


def ios_bridge_source_assets_ready(*, project_root: Path) -> bool:
    paths = resolve_ios_bridge_source_asset_paths(project_root=project_root)
    return (
        paths.workspace_package_json.exists()
        and paths.workspace_lockfile.exists()
        and paths.workspace_manifest.exists()
        and paths.ios_bridge_package_json.exists()
        and paths.workspace_node_modules.exists()
        and paths.workspace_pnpm_store.exists()
        and paths.ios_bridge_dist.exists()
        and paths.ios_bridge_node_modules.exists()
    )


def ios_bridge_runtime_assets_present(*, runtime_root: Path) -> bool:
    runtime_paths = resolve_ios_bridge_runtime_asset_paths(runtime_root=runtime_root)
    return (
        (runtime_paths.ios_bridge_dir / "dist" / "app.js").exists()
        and (runtime_paths.ios_bridge_dir / "dist" / "standalone_bootstrap.js").exists()
        and (runtime_paths.ios_bridge_dir / "node_modules").exists()
        and (runtime_paths.ios_bridge_dir / "node_modules" / "fastify-cli" / "cli.js").exists()
        and runtime_paths.sidecars_pnpm_store.exists()
        and (runtime_paths.ios_bridge_dir / "package.json").exists()
        and runtime_paths.node_bin.exists()
        and runtime_paths.node_version_marker.exists()
        and runtime_paths.node_version_marker.read_text(encoding="utf-8").strip() == NODE_RUNTIME_VERSION
    )


def ios_bridge_runtime_asset_relpaths(*, runtime_root: Path) -> dict[str, str]:
    runtime_paths = resolve_ios_bridge_runtime_asset_paths(runtime_root=runtime_root)
    if not ios_bridge_runtime_assets_present(runtime_root=runtime_root):
        raise RuntimeError(f"ios bridge runtime assets are missing under: {runtime_root}")
    return {
        "ios_bridge_relpath": os.path.relpath(runtime_paths.ios_bridge_dir, runtime_root),
        "node_relpath": os.path.relpath(runtime_paths.node_bin, runtime_root),
    }


def prepare_ios_bridge_source_assets(*, project_root: Path, force: bool = False, cwd: Path | None = None) -> None:
    paths = resolve_ios_bridge_source_asset_paths(project_root=project_root)
    if not paths.workspace_package_json.exists():
        raise RuntimeError(f"missing workspace package.json for ios bridge assets: {paths.workspace_package_json}")
    if not paths.workspace_lockfile.exists():
        raise RuntimeError(f"missing pnpm lockfile for ios bridge assets: {paths.workspace_lockfile}")
    if not paths.workspace_manifest.exists():
        raise RuntimeError(f"missing pnpm workspace manifest for ios bridge assets: {paths.workspace_manifest}")
    if not paths.ios_bridge_package_json.exists():
        raise RuntimeError(f"missing ios bridge package.json for ios bridge assets: {paths.ios_bridge_package_json}")
    pnpm_bin = ensure_pnpm_available()
    workdir = cwd or paths.workspace_root
    install_required = force or not paths.workspace_node_modules.exists() or not paths.ios_bridge_node_modules.exists()
    if install_required:
        run_command([pnpm_bin, "install", "--frozen-lockfile"], cwd=workdir)
    build_required = force or not paths.ios_bridge_dist.exists()
    if build_required:
        run_command([pnpm_bin, "-r", "build"], cwd=workdir)


def copy_ios_bridge_runtime_assets(*, project_root: Path, runtime_root: Path, download_dir: Path) -> dict[str, str]:
    source_paths = resolve_ios_bridge_source_asset_paths(project_root=project_root)
    if not ios_bridge_source_assets_ready(project_root=project_root):
        raise RuntimeError(
            "ios bridge source assets are not ready; run prepare_ios_bridge_source_assets() before copying them "
            f"from {project_root}"
        )
    runtime_paths = resolve_ios_bridge_runtime_asset_paths(runtime_root=runtime_root)
    preserve_symlinks = normalized_platform() != "windows"
    if runtime_paths.ios_bridge_dir.exists():
        shutil.rmtree(runtime_paths.ios_bridge_dir)
    if runtime_paths.sidecars_node_modules_dir.exists():
        shutil.rmtree(runtime_paths.sidecars_node_modules_dir)
    runtime_paths.ios_bridge_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_paths.ios_bridge_dist, runtime_paths.ios_bridge_dir / "dist")
    runtime_paths.sidecars_pnpm_store.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_paths.workspace_pnpm_store, runtime_paths.sidecars_pnpm_store, symlinks=preserve_symlinks)
    shutil.copytree(
        source_paths.ios_bridge_node_modules,
        runtime_paths.ios_bridge_dir / "node_modules",
        symlinks=preserve_symlinks,
    )
    shutil.copy2(source_paths.ios_bridge_package_json, runtime_paths.ios_bridge_dir / "package.json")
    if preserve_symlinks:
        rewrite_runtime_bridge_node_module_symlinks(
            source_node_modules=source_paths.ios_bridge_node_modules,
            runtime_node_modules=runtime_paths.ios_bridge_dir / "node_modules",
            source_pnpm_store=source_paths.workspace_pnpm_store,
            runtime_pnpm_store=runtime_paths.sidecars_pnpm_store,
        )
    install_bundled_node_runtime(runtime_root=runtime_root, download_dir=download_dir)
    return ios_bridge_runtime_asset_relpaths(runtime_root=runtime_root)
