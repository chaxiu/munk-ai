from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.command.build_py import build_py as _build_py

_COMPILED_MODULES = (
    "engine",
    "ocr",
    "icon",
    "fusion",
    "geometry",
)
_LEGACY_RESOURCE_SUBDIR = Path("resources") / "icon_detect"
_CURRENT_EGG_INFO_DIRNAME = "munk_perception_full_sdk.egg-info"
_ENABLE_CYTHON_ENV = "MUNK_ENABLE_CYTHON"
_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def cython_enabled() -> bool:
    return os.environ.get(_ENABLE_CYTHON_ENV, "").strip().lower() in _TRUTHY_VALUES


class build_py(_build_py):
    """Exclude compiled implementation modules from the built wheel."""

    def run(self) -> None:
        legacy_resource_dir = Path(self.build_lib) / "munk_perception_full" / _LEGACY_RESOURCE_SUBDIR
        if legacy_resource_dir.exists():
            import shutil

            shutil.rmtree(legacy_resource_dir)
        super().run()

    def find_package_modules(self, package: str, package_dir: str) -> list[Any]:
        modules: list[Any] = super().find_package_modules(package, package_dir)
        if package != "munk_perception_full" or not ENABLE_CYTHON:
            return modules
        return [module for module in modules if module[1] not in _COMPILED_MODULES]

    def find_data_files(self, package: str, src_dir: str) -> list[str]:
        files: list[str] = super().find_data_files(package, src_dir)
        if package != "munk_perception_full":
            return files
        excluded_generated_sources = {f"{module_name}.c" for module_name in _COMPILED_MODULES}
        filtered_files = []
        for file_name in files:
            path = Path(file_name)
            if path.name in excluded_generated_sources:
                continue
            if _LEGACY_RESOURCE_SUBDIR in path.parents:
                continue
            filtered_files.append(file_name)
        return filtered_files


class build_ext(_build_ext):
    """Remove generated C sources from the wheel staging directory."""

    def run(self) -> None:
        super().run()
        build_lib_dir = Path(self.build_lib) / "munk_perception_full"
        for module_name in _COMPILED_MODULES:
            (build_lib_dir / f"{module_name}.c").unlink(missing_ok=True)
        legacy_resource_dir = build_lib_dir / _LEGACY_RESOURCE_SUBDIR
        if legacy_resource_dir.exists():
            import shutil

            shutil.rmtree(legacy_resource_dir)


extensions = [
    Extension(
        name=f"munk_perception_full.{module_name}",
        sources=[f"src/munk_perception_full/{module_name}.c"],
    )
    for module_name in _COMPILED_MODULES
]

project_root = Path(__file__).resolve().parent


def _prune_stale_egg_info_dirs() -> None:
    src_dir = project_root / "src"
    if not src_dir.exists():
        return
    for egg_info_dir in src_dir.glob("*.egg-info"):
        if egg_info_dir.name == _CURRENT_EGG_INFO_DIRNAME or not egg_info_dir.is_dir():
            continue
        import shutil

        shutil.rmtree(egg_info_dir)


def _sanitize_sources_manifest() -> None:
    manifest_path = project_root / "src" / _CURRENT_EGG_INFO_DIRNAME / "SOURCES.txt"
    if not manifest_path.exists():
        return
    excluded_generated_sources = {
        f"src/munk_perception_full/{module_name}.c" for module_name in _COMPILED_MODULES
    }
    legacy_prefix = "src/munk_perception_full/resources/icon_detect/"
    original_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    filtered_lines = [
        line
        for line in original_lines
        if not Path(line).is_absolute()
        and line not in excluded_generated_sources
        and not line.startswith(legacy_prefix)
    ]
    if filtered_lines != original_lines:
        manifest_path.write_text("\n".join(filtered_lines) + "\n", encoding="utf-8")

_prune_stale_egg_info_dirs()
_sanitize_sources_manifest()
ENABLE_CYTHON = cython_enabled()
compiled_extensions = extensions if ENABLE_CYTHON else []
for extension in compiled_extensions:
    extension.sources = [
        source if not Path(source).is_absolute() else Path(source).resolve().relative_to(project_root).as_posix()
        for source in extension.sources
    ]


setup(
    ext_modules=compiled_extensions,
    cmdclass={"build_py": build_py, "build_ext": build_ext},
)
