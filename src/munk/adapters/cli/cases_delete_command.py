from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.planning.plan_mutation_service import PlanMutationService


def cases_delete_command(*, app_id: str, plan_id: str, case_id: str, json_output: bool) -> None:
    try:
        result = PlanMutationService().delete_case(app_id, plan_id, case_id)
        payload = build_success_response(
            command="plans_case_delete",
            data={
                "app_id": result.plan.app_id,
                "plan_id": result.plan.plan_id,
                "case_id": result.case_id,
                "case_count": len(result.plan.cases),
            },
        )
    except Exception as exc:
        handle_cli_error(command="plans_case_delete", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"app_id={payload['data']['app_id']}")
    typer.echo(f"plan_id={payload['data']['plan_id']}")
    typer.echo(f"case_id={payload['data']['case_id']}")
    typer.echo("status=deleted")
