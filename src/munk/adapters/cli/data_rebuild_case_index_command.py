from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import emit_json_response
from munk.planning.index_store import PlanCaseIndexStore
from munk.planning.storage import PlanStore


def data_rebuild_case_index_command(*, json_output: bool) -> None:
    store = PlanStore()
    summary = PlanCaseIndexStore(store.root_dir).rebuild_from_plan_store(store)
    payload = {
        "ok": True,
        "command": "data_rebuild_case_index",
        "data": {
            "plan_count": summary.plan_count,
            "case_count": summary.case_count,
            "db_path": str(summary.db_path),
        },
    }
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"plan_count={summary.plan_count}")
    typer.echo(f"case_count={summary.case_count}")
    typer.echo(f"db_path={summary.db_path}")
