from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.app_assets.service import AppAssetService
from munk.services.machine_contracts import InvalidMachineRequestError


def apps_list_command(*, platform: str | None, json_output: bool) -> None:
    try:
        if platform is not None and platform not in {"android", "ios", "web"}:
            raise InvalidMachineRequestError(f"unsupported platform '{platform}'")
        service = AppAssetService()
        items = []
        for profile in service.list_profiles(platform=platform):
            usage = service.get_app_usage(profile.app_id)
            items.append(
                {
                    "app_id": profile.app_id,
                    "app_name": profile.app_name,
                    "platform": profile.platform,
                    "entry_identity": profile.entry_identity,
                    "introduction_exists": service.app_registry.introduction_path(
                        profile.app_id,
                        ref=profile.app_introduction_ref,
                    ).exists(),
                    "plan_count": usage.plan_count,
                    "case_count": usage.case_count,
                }
            )
        payload = build_success_response(command="apps_list", data={"items": items})
    except Exception as exc:
        handle_cli_error(command="apps_list", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    for item in payload["data"]["items"]:
        typer.echo(
            f"app_id={item['app_id']} app_name={item['app_name'] or ''} "
            f"platform={item['platform']} entry_identity={item['entry_identity']} "
            f"plan_count={item['plan_count']} case_count={item['case_count']}"
        )
