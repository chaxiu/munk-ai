from __future__ import annotations

import json
from pathlib import Path

from .models import (
    EntryPointDescriptor,
    InstalledDistributionDescriptor,
    PythonRuntimeDescriptor,
    RuntimeDistributionManifest,
    RuntimeLayerDescriptor,
    RuntimePathDescriptor,
    SidecarDescriptor,
)
from .registry import build_runtime_layer_specs

MANIFEST_FILE_NAME = "manifest.lock"
RUNTIME_MANIFEST_SCHEMA_VERSION = "phase7gi.runtime_manifest.v1"


def load_runtime_manifest(path: Path) -> RuntimeDistributionManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RuntimeDistributionManifest.model_validate(payload)


def write_runtime_manifest(path: Path, manifest: RuntimeDistributionManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_runtime_manifest(
    *,
    platform: str,
    arch: str,
    variant: str,
    python_version: str,
    pbs_release_tag: str,
    pbs_archive_flavor: str,
    pbs_target_triple: str,
    python_root_relpath: str,
    python_executable_relpath: str,
    site_packages_relpath: str,
    installed_distributions: list[InstalledDistributionDescriptor],
    adb_relpath: str,
    launcher_relpath: str,
    recording_ui_relpath: str | None = None,
    recording_bridge_relpath: str | None = None,
    node_relpath: str | None = None,
) -> RuntimeDistributionManifest:
    packages_by_layer: dict[str, list[str]] = {}
    for distribution in installed_distributions:
        packages_by_layer.setdefault(distribution.layer, []).append(distribution.name)
    sidecars = {"adb": SidecarDescriptor(path=adb_relpath, owner="core", kind="adb")}
    if recording_bridge_relpath is not None:
        sidecars["recording_bridge"] = SidecarDescriptor(
            path=recording_bridge_relpath,
            owner="core",
            kind="recording_bridge",
        )
    if node_relpath is not None:
        sidecars["node"] = SidecarDescriptor(path=node_relpath, owner="core", kind="node")
    core_owned_resources = ["resources/core"]
    if recording_ui_relpath is not None:
        core_owned_resources.append(recording_ui_relpath)
    layers = {
        "core": RuntimeLayerDescriptor(
            packages=packages_by_layer.get("core", []),
            owned_code=[
                python_root_relpath,
                site_packages_relpath,
            ],
            owned_resources=core_owned_resources,
            owned_data=[
                "data/runs",
                "data/operations",
            ],
            owned_binaries=[launcher_relpath],
        )
    }
    for layer_name, layer_spec in build_runtime_layer_specs().items():
        packages = packages_by_layer.get(layer_name)
        if not packages:
            continue
        layers[layer_name] = RuntimeLayerDescriptor(
            provider=layer_spec.provider,
            runtime=layer_spec.runtime,
            packages=packages,
            resource_mode=layer_spec.resource_mode,
            owned_resources=[
                template.format(site_packages_relpath=site_packages_relpath)
                for template in layer_spec.owned_resource_templates
            ],
            owned_data=list(layer_spec.owned_data_relpaths),
        )
    return RuntimeDistributionManifest(
        schema_version=RUNTIME_MANIFEST_SCHEMA_VERSION,
        platform=platform,
        arch=arch,
        variant=variant,
        python_runtime=PythonRuntimeDescriptor(
            kind="python-build-standalone",
            root=python_root_relpath,
            executable=python_executable_relpath,
            version=python_version,
            release_tag=pbs_release_tag,
            archive_flavor=pbs_archive_flavor,
            target_triple=pbs_target_triple,
            site_packages=site_packages_relpath,
        ),
        entrypoints={
            "monkey_ai": EntryPointDescriptor(path=launcher_relpath, owner="core"),
        },
        sidecars=sidecars,
        layers=layers,
        installed_distributions=list(installed_distributions),
        paths=RuntimePathDescriptor(
            bin_root="bin",
            python_root=python_root_relpath,
            site_packages_root=site_packages_relpath,
            data_root="data",
            sidecars_root="sidecars",
            core_resources_root="resources/core",
        ),
    )


def validate_runtime_manifest_contract(
    runtime_root: Path,
    manifest: RuntimeDistributionManifest,
) -> list[str]:
    errors: list[str] = []
    required_paths = [
        manifest.paths.bin_root,
        manifest.paths.python_root,
        manifest.paths.site_packages_root,
        manifest.paths.data_root,
        manifest.paths.sidecars_root,
        manifest.paths.core_resources_root,
        manifest.python_runtime.executable,
        manifest.python_runtime.site_packages,
    ]
    required_paths.extend(entry.path for entry in manifest.entrypoints.values())
    required_paths.extend(sidecar.path for sidecar in manifest.sidecars.values())
    for layer in manifest.layers.values():
        required_paths.extend(layer.owned_code)
        required_paths.extend(layer.owned_resources)
        required_paths.extend(layer.owned_data)
        required_paths.extend(layer.owned_binaries)
        required_paths.extend(layer.owned_config)
    for relpath in sorted(set(required_paths)):
        if not (runtime_root / relpath).exists():
            errors.append(f"missing runtime path declared in manifest: {relpath}")
    return errors
