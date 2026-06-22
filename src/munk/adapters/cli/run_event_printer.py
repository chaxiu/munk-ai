from __future__ import annotations

import typer

from munk.services.events import (
    RunEvent,
    RunEventType,
    run_event_action,
    run_event_attempt,
    run_event_duration_ms,
    run_event_element_count,
    run_event_error_message,
    run_event_error_type,
    run_event_reason,
    run_event_seeded_element_count,
    run_event_step,
    run_event_summary,
    run_event_will_retry,
)


def print_run_event(event: RunEvent) -> None:
    if event.type == RunEventType.LOG:
        return
    if event.type == RunEventType.STEP_STARTED:
        typer.echo(f"step={run_event_step(event)} started", err=True)
        return
    if event.type == RunEventType.PERCEPTION_COMPLETED:
        typer.echo(
            f"step={run_event_step(event)} elements={run_event_element_count(event)}",
            err=True,
        )
        return
    if event.type == RunEventType.RUNNER_CONTRACT_MISS:
        typer.echo(
            (
                f"step={run_event_step(event)} "
                f"contract_miss attempt={run_event_attempt(event)} "
                f"seeded={run_event_seeded_element_count(event)} "
                f"retrying={'yes' if run_event_will_retry(event) else 'no'}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.ACTION_PROPOSED:
        typer.echo(
            (
                f"step={run_event_step(event)} "
                f"action={run_event_action(event)} "
                f"summary={run_event_summary(event)}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.ACTION_EXECUTION_STARTED:
        typer.echo(
            (
                f"step={run_event_step(event)} "
                f"executing action={run_event_action(event)} "
                f"summary={run_event_summary(event)}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.ACTION_EXECUTED:
        typer.echo(
            (
                f"step={run_event_step(event)} "
                f"action_done={run_event_action(event)} "
                f"duration_ms={run_event_duration_ms(event)}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.ACTION_EXECUTION_FAILED:
        typer.echo(
            (
                f"step={run_event_step(event)} "
                f"action_failed={run_event_action(event)} "
                f"error={run_event_error_type(event) or 'ActionExecutionError'} "
                f"message={run_event_error_message(event)}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.RUN_STOPPED:
        typer.echo(f"run stopped: {run_event_reason(event)}", err=True)
        return
    if event.type == RunEventType.RUN_FAILED:
        typer.echo(f"run failed: {event.message}", err=True)
