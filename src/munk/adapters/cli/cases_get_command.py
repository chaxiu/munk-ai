from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.planning.storage import PlanStore
from munk.services.machine_contracts import InvalidMachineRequestError


def cases_get_command(*, app_id: str, plan_id: str, case_id: str, json_output: bool) -> None:
    try:
        plan = PlanStore().load(app_id, plan_id)
        case = next((item for item in plan.cases if item.case_id == case_id), None)
        if case is None:
            raise InvalidMachineRequestError(f"case '{case_id}' not found in plan '{app_id}/{plan_id}'")
        budget = case.budget
        payload = build_success_response(
            command="plans_case_get",
            data={
                "app_id": plan.app_id,
                "plan_id": plan.plan_id,
                "plan_source": plan.source,
                "plan_version": plan.version,
                "case_id": case.case_id,
                "title": case.title,
                "intent": case.intent,
                "preconditions": list(case.preconditions),
                "expected": list(case.expected),
                "procedure": list(case.procedure),
                "post_action": list(case.post_action),
                "is_core_case": case.is_core_case,
                "runner_goal": case.runner_goal,
                "start_mode": case.start_state.mode,
                "start_page_id": case.start_state.page_id,
                "max_steps": budget.max_steps if budget is not None else None,
                "max_seconds": budget.max_seconds if budget is not None else None,
            },
        )
    except FileNotFoundError:
        handle_cli_error(
            command="plans_case_get",
            exc=InvalidMachineRequestError(f"plan '{app_id}/{plan_id}' not found"),
            json_output=json_output,
        )
    except Exception as exc:
        handle_cli_error(command="plans_case_get", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"app_id={payload['data']['app_id']}")
    typer.echo(f"plan_id={payload['data']['plan_id']}")
    typer.echo(f"case_id={payload['data']['case_id']}")
    typer.echo(f"title={payload['data']['title']}")
    typer.echo(f"start_mode={payload['data']['start_mode']}")
