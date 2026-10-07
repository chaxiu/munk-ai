from __future__ import annotations

from pathlib import Path

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.adapters.cli.plan_request_io import load_case_upsert_request
from munk.planning.plan_mutation_service import PlanMutationService
from munk.testing import TestCase


def cases_add_command(*, app_id: str, plan_id: str, request_file: Path, json_output: bool) -> None:
    try:
        request = load_case_upsert_request(request_file)
        result = PlanMutationService().add_case(app_id, plan_id, request.to_test_case())
        payload = build_success_response(
            command="plans_case_add",
            data=_case_detail_data(result.plan.app_id, result.plan.plan_id, result.plan.source, result.plan.version, result.case),
        )
    except Exception as exc:
        handle_cli_error(command="plans_case_add", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"app_id={payload['data']['app_id']}")
    typer.echo(f"plan_id={payload['data']['plan_id']}")
    typer.echo(f"case_id={payload['data']['case_id']}")
    typer.echo("status=added")


def _case_detail_data(
    app_id: str,
    plan_id: str,
    plan_source: str,
    plan_version: str,
    case: TestCase,
) -> dict[str, object]:
    budget = case.budget
    return {
        "app_id": app_id,
        "plan_id": plan_id,
        "plan_source": plan_source,
        "plan_version": plan_version,
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
    }
