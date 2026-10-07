from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.app_assets.service import AppAssetService
from munk.services.knowledge import KnowledgeCandidateApprovalService


def knowledge_candidates_list_command(
    *,
    app_id: str,
    status: str | None,
    candidate_id: str | None,
    limit: int,
    json_output: bool,
) -> None:
    try:
        app_service = AppAssetService()
        service = KnowledgeCandidateApprovalService(assets_root=app_service.app_registry.root_dir)
        result = service.list_candidates(
            app_id=app_id,
            status=status,
            candidate_id=candidate_id,
            limit=limit,
        )
        payload = build_success_response(
            command="knowledge_candidates_list",
            data={
                "items": [item.model_dump(mode="json") for item in result.items],
                "total_count": result.total_count,
            },
        )
    except Exception as exc:
        handle_cli_error(command="knowledge_candidates_list", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    for item in payload["data"]["items"]:
        typer.echo(
            f"candidate_id={item['candidate_id']} status={item['status']} "
            f"card_type={item['candidate']['card_type']} title={item['candidate']['title']}"
        )
