from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.adapters.shared.plan_queries import list_plans_payload
from munk.planning.index_store import PlanCaseIndexStore


def plans_list_command(*, app_id: str | None, source: str | None, limit: int, json_output: bool) -> None:
    try:
        data = list_plans_payload(
            index_store=PlanCaseIndexStore(),
            app_id=app_id,
            source=source,
            case_count_mode=None,
            limit=limit,
            offset=0,
        )
        payload = build_success_response(command="plans_list", data={"items": data.items})
    except Exception as exc:
        handle_cli_error(command="plans_list", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    for item in payload["data"]["items"]:
        typer.echo(
            f"app_id={item['app_id']} plan_id={item['plan_id']} source={item['source']} "
            f"version={item['version']} case_count={item['case_count']} updated_at={item['updated_at']}"
        )
