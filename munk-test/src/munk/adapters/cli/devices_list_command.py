from __future__ import annotations

from typing import Literal, cast

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.device import (
    DeviceDescriptor,
    SupportsDeviceDiscovery,
    list_device_runtime_factories,
    resolve_device_runtime_factory,
)
from munk.paths import export_adb_env
from munk.services.machine_contracts import InvalidMachineRequestError

AppPlatform = Literal["android", "ios", "web"]


def devices_list_command(*, platform: str | None, json_output: bool) -> None:
    try:
        items = [_device_payload(item) for item in _list_discovered_devices(platform)]
        payload = build_success_response(command="devices_list", data={"items": items})
    except Exception as exc:
        handle_cli_error(command="devices_list", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    for item in payload["data"]["items"]:
        typer.echo(
            f"platform={item['platform']} device_ref={item['device_ref']} display_name={item['display_name']} "
            f"kind={item['kind']} availability={item['availability']} is_booted={item['is_booted']}"
        )


def _list_discovered_devices(platform: str | None) -> list[DeviceDescriptor]:
    export_adb_env()
    if platform is not None:
        if platform not in {"android", "ios", "web"}:
            raise InvalidMachineRequestError(f"unsupported platform '{platform}'")
        factory = resolve_device_runtime_factory(platform=cast(AppPlatform, platform))
        if not isinstance(factory, SupportsDeviceDiscovery):
            raise InvalidMachineRequestError(f"device discovery is not available for platform '{platform}'")
        return factory.list_device_descriptors()

    items: list[DeviceDescriptor] = []
    for factory in list_device_runtime_factories().values():
        if isinstance(factory, SupportsDeviceDiscovery):
            items.extend(factory.list_device_descriptors())
    return sorted(items, key=lambda item: (item.platform, item.kind, item.display_name.lower(), item.device_ref))


def _device_payload(descriptor: DeviceDescriptor) -> dict[str, object]:
    return {
        "platform": descriptor.platform,
        "device_ref": descriptor.device_ref,
        "display_name": descriptor.display_name,
        "kind": descriptor.kind,
        "availability": descriptor.availability,
        "is_booted": descriptor.is_booted,
        "raw": dict(descriptor.raw),
    }
