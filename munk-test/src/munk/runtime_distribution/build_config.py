from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from .build_env import DependencyProject
from .registry import CORE_PACKAGE_SPECS, PackageSpec, feature_is_enabled, iter_feature_specs


class WorkspaceSection(TypedDict):
    name: str
    install_mode: str
    editable_projects: list[DependencyProject]


def resolve_workspace_sections(*, build_config: Path, project_root: Path) -> list[WorkspaceSection]:
    raw = _parse_simple_yaml_sections(build_config)
    sections = [_resolve_core_section(raw=raw, build_config=build_config, project_root=project_root)]
    for feature in iter_feature_specs():
        section = _resolve_feature_section(
            feature_name=feature.name,
            raw=raw,
            build_config=build_config,
            project_root=project_root,
        )
        if section is not None:
            sections.append(section)
    sections.append(
        WorkspaceSection(
            name="main",
            install_mode="editable",
            editable_projects=[DependencyProject(name="munk", project_dir=project_root)],
        )
    )
    return sections


def flatten_workspace_projects(sections: list[WorkspaceSection]) -> list[DependencyProject]:
    ordered: list[DependencyProject] = []
    seen: set[str] = set()
    for section in sections:
        for project in section["editable_projects"]:
            if project.name in seen:
                continue
            ordered.append(project)
            seen.add(project.name)
    return ordered


def _resolve_core_section(
    *,
    raw: dict[str, dict[str, str]],
    build_config: Path,
    project_root: Path,
) -> WorkspaceSection:
    editable_projects = [
        DependencyProject(
            name=package.name,
            project_dir=_resolve_workspace_path(
                raw_value=_raw_value_for_package(raw=raw, package=package),
                build_config=build_config,
                project_root=project_root,
                default_paths=[project_root / package.default_relpath],
                label=_package_label(package),
            ),
        )
        for package in CORE_PACKAGE_SPECS
    ]
    return WorkspaceSection(name="core", install_mode="editable", editable_projects=editable_projects)


def _resolve_feature_section(
    *,
    feature_name: str,
    raw: dict[str, dict[str, str]],
    build_config: Path,
    project_root: Path,
) -> WorkspaceSection | None:
    feature = next(candidate for candidate in iter_feature_specs() if candidate.name == feature_name)
    if not feature_is_enabled(raw, feature_name=feature_name):
        return None
    section = raw.get(feature_name, {})
    if feature.runtime_name is not None:
        runtime_name = section.get("runtime_name", feature.runtime_name)
        if runtime_name != feature.runtime_name:
            raise RuntimeError(f"{feature_name}.runtime_name must be {feature.runtime_name!r}, got: {runtime_name}")
    if feature.provider_name is not None:
        provider_name = section.get("provider_name", feature.provider_name)
        if provider_name != feature.provider_name:
            raise RuntimeError(f"{feature_name}.provider_name must be {feature.provider_name!r}, got: {provider_name}")
    install_mode = section.get("install_mode", feature.install_mode)
    if install_mode != feature.install_mode:
        raise RuntimeError(f"{feature_name}.install_mode must be {feature.install_mode!r}, got: {install_mode}")
    editable_projects = [
        DependencyProject(
            name=package.name,
            project_dir=_resolve_workspace_path(
                raw_value=_raw_value_for_package(raw=raw, package=package),
                build_config=build_config,
                project_root=project_root,
                default_paths=[project_root / package.default_relpath],
                label=_package_label(package),
            ),
        )
        for package in feature.package_specs
    ]
    return WorkspaceSection(
        name=feature_name,
        install_mode=feature.install_mode,
        editable_projects=editable_projects,
    )


def _raw_value_for_package(*, raw: dict[str, dict[str, str]], package: PackageSpec) -> str | None:
    if package.config_section is None or package.config_key is None:
        return None
    return raw.get(package.config_section, {}).get(package.config_key)


def _package_label(package: PackageSpec) -> str:
    if package.config_section is not None and package.config_key is not None:
        return f"{package.config_section}.{package.config_key}"
    return package.name


def _resolve_workspace_path(
    *,
    raw_value: str | None,
    build_config: Path,
    project_root: Path,
    default_paths: list[Path],
    label: str,
) -> Path:
    if raw_value is None or not raw_value.strip():
        for default_path in default_paths:
            if default_path.exists():
                return default_path.resolve()
        attempted = ", ".join(str(path) for path in default_paths)
        raise RuntimeError(f"missing {label} and default path does not exist; tried: {attempted}")
    expanded = Path(raw_value).expanduser()
    if expanded.is_absolute():
        resolved = expanded.resolve()
        if not resolved.exists():
            raise RuntimeError(f"path for {label} does not exist: {resolved}")
        return resolved
    candidates = [
        (build_config.parent / expanded).resolve(),
        (project_root / expanded).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(
        f"path for {label} does not exist; tried: {', '.join(str(candidate) for candidate in candidates)}"
    )


def _parse_simple_yaml_sections(build_config: Path) -> dict[str, dict[str, str]]:
    if not build_config.exists():
        return {}
    sections: dict[str, dict[str, str]] = {}
    current_section: str | None = None
    for raw_line in build_config.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw_line.startswith(" ") and line.endswith(":"):
            current_section = line[:-1].strip()
            sections.setdefault(current_section, {})
            continue
        if current_section is None:
            continue
        if not raw_line.startswith("  ") or ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        sections[current_section][key.strip()] = _strip_yaml_scalar(value.strip())
    return sections


def _strip_yaml_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
