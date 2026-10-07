from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.app_assets.service import AppAssetService
from munk.services.knowledge import KnowledgeCandidateApprovalService


def knowledge_candidates_reject_command(
    *,
    app_id: str,
    candidate_id: str,
    reviewed_by: str | None,
    review_note: str | None,
    json_output: bool,
) -> None:
    try:
        app_service = AppAssetService()
        service = KnowledgeCandidateApprovalService(assets_root=app_service.app_registry.root_dir)
        result = service.reject_candidate(
            app_id=app_id,
            candidate_id=candidate_id,
            reviewed_by=reviewed_by,
            review_note=review_note,
        )
        payload = build_success_response(
            command="knowledge_candidates_reject",
            data=result.model_dump(mode="json"),
        )
    except Exception as exc:
        handle_cli_error(command="knowledge_candidates_reject", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(
        f"candidate_id={payload['data']['candidate']['candidate_id']} "
        f"status={payload['data']['candidate']['status']}"
    )
