from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

PLATFORM_TO_REPOSITORY_SUFFIX = {
    "macos": "darwin",
    "linux": "linux",
    "windows": "win",
}
PBS_TARGET_TRIPLES = {
    ("macos", "arm64"): "aarch64-apple-darwin",
    ("macos", "x86_64"): "x86_64-apple-darwin",
    ("linux", "arm64"): "aarch64-unknown-linux-gnu",
    ("linux", "x86_64"): "x86_64-unknown-linux-gnu",
    ("windows", "arm64"): "aarch64-pc-windows-msvc",
    ("windows", "x86_64"): "x86_64-pc-windows-msvc",
}


@dataclass(frozen=True)
class RuntimeBuildTarget:
    platform: str
    arch: str


def normalized_platform(system_name: str | None = None) -> str:
    system = (system_name or platform.system()).lower()
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    if system == "windows":
        return "windows"
    return system


def normalized_arch(machine_name: str | None = None) -> str:
    machine = (machine_name or platform.machine()).lower()
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    return machine


def resolve_host_target() -> RuntimeBuildTarget:
    return RuntimeBuildTarget(platform=normalized_platform(), arch=normalized_arch())


def ensure_supported_platform(platform_name: str | None = None, arch: str | None = None) -> RuntimeBuildTarget:
    target = RuntimeBuildTarget(
        platform=platform_name or normalized_platform(),
        arch=arch or normalized_arch(),
    )
    if (target.platform, target.arch) not in PBS_TARGET_TRIPLES:
        raise RuntimeError(f"unsupported standalone runtime target: {target.platform}/{target.arch}")
    return target


def pbs_target_triple(*, platform_name: str | None = None, arch: str | None = None) -> str:
    target = ensure_supported_platform(platform_name=platform_name, arch=arch)
    return PBS_TARGET_TRIPLES[(target.platform, target.arch)]


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


def node_distribution_target(*, platform_name: str | None = None, arch: str | None = None) -> str:
    target = ensure_supported_platform(platform_name=platform_name, arch=arch)
    node_os = {
        "macos": "darwin",
        "linux": "linux",
        "windows": "win",
    }[target.platform]
    node_arch = {
        "arm64": "arm64",
        "x86_64": "x64",
    }.get(target.arch)
    if node_arch is None:
        raise RuntimeError(f"unsupported architecture for bundled node runtime: {target.arch}")
    return f"{node_os}-{node_arch}"


def build_pinned_node_distribution_url(
    *,
    node_runtime_version: str,
    platform_name: str | None = None,
    arch: str | None = None,
) -> str:
    target = ensure_supported_platform(platform_name=platform_name, arch=arch)
    extension = ".zip" if target.platform == "windows" else ".tar.xz" if target.platform == "linux" else ".tar.gz"
    asset_name = (
        f"node-{node_runtime_version}-"
        f"{node_distribution_target(platform_name=target.platform, arch=target.arch)}{extension}"
    )
    return f"https://nodejs.org/dist/{node_runtime_version}/{asset_name}"
