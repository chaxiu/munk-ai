from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.app_assets.service import AppAssetService
from munk.services.machine_contracts import InvalidMachineRequestError


def apps_get_command(*, app_id: str, json_output: bool) -> None:
    try:
        detail = AppAssetService().build_app_detail(app_id)
        payload = build_success_response(
            command="apps_get",
            data={
                "profile": detail.profile.model_dump(mode="json"),
                "introduction_markdown": detail.introduction_markdown,
                "app_knowledge_content": detail.app_knowledge_content,
                "app_knowledge_exists": detail.app_knowledge_exists,
                "app_target": detail.profile.to_app_target().model_dump(mode="json"),
                "plan_count": detail.usage.plan_count,
                "case_count": detail.usage.case_count,
            },
        )
    except FileNotFoundError:
        handle_cli_error(
            command="apps_get",
            exc=InvalidMachineRequestError(f"app '{app_id}' not found"),
            json_output=json_output,
        )
    except Exception as exc:
        handle_cli_error(command="apps_get", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    data = payload["data"]
    typer.echo(f"app_id={data['profile']['app_id']}")
    typer.echo(f"app_name={data['profile'].get('app_name') or ''}")
    typer.echo(f"platform={data['profile']['platform']}")
    typer.echo(f"plan_count={data['plan_count']}")
    typer.echo(f"case_count={data['case_count']}")
