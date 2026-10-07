from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class PythonRuntimeDescriptor(BaseModel):
    kind: str
    root: str
    executable: str
    version: str
    release_tag: str
    archive_flavor: str
    target_triple: str
    site_packages: str


class RuntimePathDescriptor(BaseModel):
    bin_root: str
    python_root: str
    site_packages_root: str
    data_root: str
    sidecars_root: str
    core_resources_root: str


class EntryPointDescriptor(BaseModel):
    path: str
    owner: str


class SidecarDescriptor(BaseModel):
    path: str
    owner: str
    kind: str


class InstalledDistributionDescriptor(BaseModel):
    name: str
    version: str
    layer: str


class RuntimeLayerDescriptor(BaseModel):
    packages: list[str] = Field(default_factory=list)
    provider: str | None = None
    runtime: str | None = None
    resource_mode: str | None = None
    owned_code: list[str] = Field(default_factory=list)
    owned_resources: list[str] = Field(default_factory=list)
    owned_data: list[str] = Field(default_factory=list)
    owned_binaries: list[str] = Field(default_factory=list)
    owned_config: list[str] = Field(default_factory=list)


class RuntimeDistributionManifest(BaseModel):
    schema_version: str
    platform: str
    arch: str
    variant: str
    python_runtime: PythonRuntimeDescriptor
    entrypoints: dict[str, EntryPointDescriptor] = Field(default_factory=dict)
    sidecars: dict[str, SidecarDescriptor] = Field(default_factory=dict)
    layers: dict[str, RuntimeLayerDescriptor] = Field(default_factory=dict)
    installed_distributions: list[InstalledDistributionDescriptor] = Field(default_factory=list)
    paths: RuntimePathDescriptor


@dataclass(frozen=True)
class ResolvedRuntimeLayout:
    layout_mode: Literal["distribution", "development"]
    runtime_root: Path
    manifest_path: Path | None
    python_root: Path | None
    bin_root: Path
    sidecars_root: Path | None
    data_root: Path
    core_resources_root: Path
    adb_path: Path
    project_root: Path
    manifest: RuntimeDistributionManifest | None = None
