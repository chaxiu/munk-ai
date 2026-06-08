from __future__ import annotations

import typer

from munk.services.events import RunEvent, RunEventType


def print_run_event(event: RunEvent) -> None:
    if event.type == RunEventType.LOG:
        return
    if event.type == RunEventType.STEP_STARTED:
        typer.echo(f"step={event.data.get('step')} started", err=True)
        return
    if event.type == RunEventType.PERCEPTION_COMPLETED:
        typer.echo(
            f"step={event.data.get('step')} elements={event.data.get('element_count')}",
            err=True,
        )
        return
    if event.type == RunEventType.RUNNER_CONTRACT_MISS:
        typer.echo(
            (
                f"step={event.data.get('step')} "
                f"contract_miss attempt={event.data.get('attempt')} "
                f"seeded={event.data.get('seeded_element_count')} "
                f"retrying={'yes' if event.data.get('will_retry') else 'no'}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.ACTION_PROPOSED:
        typer.echo(
            (
                f"step={event.data.get('step')} "
                f"action={event.data.get('action')} "
                f"summary={event.data.get('summary')}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.ACTION_EXECUTION_STARTED:
        typer.echo(
            (
                f"step={event.data.get('step')} "
                f"executing action={event.data.get('action')} "
                f"summary={event.data.get('summary')}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.ACTION_EXECUTED:
        typer.echo(
            (
                f"step={event.data.get('step')} "
                f"action_done={event.data.get('action')} "
                f"duration_ms={event.data.get('duration_ms')}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.ACTION_EXECUTION_FAILED:
        typer.echo(
            (
                f"step={event.data.get('step')} "
                f"action_failed={event.data.get('action')} "
                f"error={event.data.get('error_type') or 'ActionExecutionError'} "
                f"message={event.data.get('error_message')}"
            ),
            err=True,
        )
        return
    if event.type == RunEventType.RUN_STOPPED:
        typer.echo(f"run stopped: {event.data.get('reason')}", err=True)
        return
    if event.type == RunEventType.RUN_FAILED:
        typer.echo(f"run failed: {event.message}", err=True)
