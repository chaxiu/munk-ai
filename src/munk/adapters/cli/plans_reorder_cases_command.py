from __future__ import annotations

from pathlib import Path

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.adapters.cli.plan_request_io import load_case_reorder_request
from munk.planning.plan_mutation_service import PlanMutationService


def plans_reorder_cases_command(*, app_id: str, plan_id: str, request_file: Path, json_output: bool) -> None:
    try:
        request = load_case_reorder_request(request_file)
        plan = PlanMutationService().reorder_cases(app_id, plan_id, request.case_ids)
        payload = build_success_response(
            command="plans_cases_reorder",
            data={
                "app_id": plan.app_id,
                "plan_id": plan.plan_id,
                "source": plan.source,
                "version": plan.version,
                "case_count": len(plan.cases),
                "cases": [
                    {
                        "case_id": case.case_id,
                        "title": case.title,
                        "intent": case.intent,
                        "is_core_case": case.is_core_case,
                        "runner_goal": case.runner_goal,
                        "start_mode": case.start_state.mode,
                        "start_page_id": case.start_state.page_id,
                    }
                    for case in plan.cases
                ],
            },
        )
    except Exception as exc:
        handle_cli_error(command="plans_cases_reorder", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"app_id={payload['data']['app_id']}")
    typer.echo(f"plan_id={payload['data']['plan_id']}")
    typer.echo(f"case_count={payload['data']['case_count']}")
    typer.echo("status=reordered")
