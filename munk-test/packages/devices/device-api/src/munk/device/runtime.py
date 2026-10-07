from __future__ import annotations

from importlib.metadata import entry_points
from typing import Protocol

from munk.app import AppPlatform, AppTarget

from .protocols import DeviceDriver

ENTRY_POINT_GROUP = "munk.device.runtimes"


class DeviceRuntimeFactory(Protocol):
    runtime_id: str
    supported_platforms: tuple[AppPlatform, ...]

    def create_device(
        self,
        *,
        device_ref: str | None,
        app_target: AppTarget,
    ) -> DeviceDriver: ...


def list_device_runtime_factories() -> dict[str, DeviceRuntimeFactory]:
    factories: dict[str, DeviceRuntimeFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_device_runtime_factory(*, platform: AppPlatform, runtime_name: str | None = None) -> DeviceRuntimeFactory:
    factories = list_device_runtime_factories()
    if runtime_name is not None:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise LookupError(f"device runtime '{runtime_name}' not found; available runtimes: {available}")
        if platform not in factory.supported_platforms:
            supported = ", ".join(factory.supported_platforms)
            raise LookupError(
                f"device runtime '{runtime_name}' does not support platform '{platform}'; supported: {supported}"
            )
        return factory
    matching = [factory for factory in factories.values() if platform in factory.supported_platforms]
    if not matching:
        available = ", ".join(sorted(factories)) or "none"
        raise LookupError(f"no device runtime found for platform '{platform}'; installed runtimes: {available}")
    if len(matching) > 1:
        available = ", ".join(sorted(factory.runtime_id for factory in matching))
        raise LookupError(
            f"multiple device runtimes found for platform '{platform}'; explicit runtime selection is required: "
            f"{available}"
        )
    return matching[0]
