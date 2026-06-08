from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.planning.storage import PlanStore
from munk.services.machine_contracts import InvalidMachineRequestError
from munk.testing import TestCase


def plans_get_command(*, app_id: str, plan_id: str, json_output: bool) -> None:
    try:
        plan = PlanStore().load(app_id, plan_id)
        payload = build_success_response(
            command="plans_get",
            data={
                "app_id": plan.app_id,
                "plan_id": plan.plan_id,
                "source": plan.source,
                "version": plan.version,
                "case_count": len(plan.cases),
                "cases": [_case_brief_data(case) for case in plan.cases],
            },
        )
    except FileNotFoundError as exc:
        handle_cli_error(
            command="plans_get",
            exc=InvalidMachineRequestError(f"plan '{app_id}/{plan_id}' not found"),
            json_output=json_output,
        )
        raise AssertionError("unreachable") from exc
    except Exception as exc:
        handle_cli_error(command="plans_get", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"app_id={payload['data']['app_id']}")
    typer.echo(f"plan_id={payload['data']['plan_id']}")
    typer.echo(f"source={payload['data']['source']}")
    typer.echo(f"version={payload['data']['version']}")
    typer.echo(f"case_count={payload['data']['case_count']}")


def _case_brief_data(case: TestCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "title": case.title,
        "intent": case.intent,
        "post_action": list(case.post_action),
        "is_core_case": case.is_core_case,
        "runner_goal": case.runner_goal,
        "start_mode": case.start_state.mode,
        "start_page_id": case.start_state.page_id,
    }
