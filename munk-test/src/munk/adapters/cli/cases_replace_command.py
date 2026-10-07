from __future__ import annotations

from pathlib import Path

import typer

from munk.adapters.cli.cases_add_command import _case_detail_data
from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.adapters.cli.plan_request_io import load_case_upsert_request
from munk.planning.plan_mutation_service import PlanMutationService
from munk.services.machine_contracts import InvalidMachineRequestError


def cases_replace_command(*, app_id: str, plan_id: str, case_id: str, request_file: Path, json_output: bool) -> None:
    try:
        request = load_case_upsert_request(request_file)
        if request.case.case_id != case_id:
            raise InvalidMachineRequestError("request case.case_id must match --case-id")
        result = PlanMutationService().replace_case(app_id, plan_id, case_id, request.to_test_case())
        payload = build_success_response(
            command="plans_case_replace",
            data=_case_detail_data(result.plan.app_id, result.plan.plan_id, result.plan.source, result.plan.version, result.case),
        )
    except Exception as exc:
        handle_cli_error(command="plans_case_replace", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"app_id={payload['data']['app_id']}")
    typer.echo(f"plan_id={payload['data']['plan_id']}")
    typer.echo(f"case_id={payload['data']['case_id']}")
    typer.echo("status=replaced")
