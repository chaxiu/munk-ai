from __future__ import annotations

from pathlib import Path

import typer

from munk.adapters.cli.app_request_io import load_app_upsert_request
from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.app_assets.service import AppAssetService
from munk.app_assets.storage import AppRegistry
from munk.app_knowledge import build_app_knowledge_index
from munk.services.knowledge import validate_app_knowledge_document
from munk.services.machine_contracts import InvalidMachineRequestError


def apps_update_command(*, app_id: str, request_file: Path, json_output: bool) -> None:
    try:
        request = load_app_upsert_request(request_file)
        service = AppAssetService()
        normalized_app_id = AppRegistry.normalize_app_id(app_id)
        normalized_profile_app_id = AppRegistry.normalize_app_id(request.profile.app_id)
        if not service.app_registry.exists(normalized_app_id):
            raise InvalidMachineRequestError(f"app '{app_id}' not found")
        if normalized_profile_app_id != normalized_app_id:
            raise InvalidMachineRequestError("request profile app_id must match --app-id")
        if (request.app_knowledge_content or "").strip():
            validate_app_knowledge_document(
                request.app_knowledge_content or "",
                expected_app_id=normalized_profile_app_id,
            )
        profile = request.profile.to_profile().model_copy(update={"app_id": normalized_profile_app_id})
        service.app_registry.save(profile)
        service.app_registry.save_introduction(
            profile.app_id,
            request.introduction_markdown,
            ref=profile.app_introduction_ref,
        )
        if (request.app_knowledge_content or "").strip():
            service.app_registry.save_knowledge(
                profile.app_id,
                request.app_knowledge_content or "",
                ref=profile.app_knowledge_ref,
            )
            build_app_knowledge_index(
                app_id=profile.app_id,
                assets_root=service.app_registry.root_dir,
                ref=profile.app_knowledge_ref,
            )
        detail = service.build_app_detail(profile.app_id)
        payload = build_success_response(
            command="apps_update",
            data={
                "profile": detail.profile.model_dump(mode="json"),
                "introduction_markdown": detail.introduction_markdown,
                "app_knowledge_content": detail.app_knowledge_content,
                "app_knowledge_exists": detail.app_knowledge_exists,
                "app_target": detail.profile.to_app_target().model_dump(mode="json"),
                "plan_count": detail.usage.plan_count,
                "case_count": detail.usage.case_count,
            },
        )
    except Exception as exc:
        handle_cli_error(command="apps_update", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"app_id={payload['data']['profile']['app_id']}")
    typer.echo("status=updated")
