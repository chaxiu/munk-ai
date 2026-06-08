from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import emit_json_response
from munk.adapters.local_api.client import LocalApiClient


def data_search_cases_command(
    *,
    app_id: str | None,
    plan_id: str | None,
    case_id: str | None,
    is_core_case: bool | None,
    start_mode: str | None,
    limit: int,
    json_output: bool,
) -> None:
    payload = LocalApiClient().search_cases(
        app_id=app_id,
        plan_id=plan_id,
        case_id=case_id,
        is_core_case=is_core_case,
        start_mode=start_mode,
        limit=limit,
    )
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    if payload["ok"] is False:
        typer.echo(payload["error"]["message"], err=True)
        raise typer.Exit(code=1)
    items = payload["data"]["items"]
    for item in items:
        typer.echo(
            f"app_id={item['app_id']} plan_id={item['plan_id']} case_id={item['case_id']} "
            f"title={item['title']} is_core_case={item['is_core_case']} start_mode={item['start_mode']}"
        )
