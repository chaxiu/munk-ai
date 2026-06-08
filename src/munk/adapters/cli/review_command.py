from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

import typer

from munk.adapters.cli.machine_io import (
    emit_json_response,
    handle_cli_error,
    load_json_request,
    reject_mixed_request_file_usage,
)
from munk.adapters.shared.machine_requests import ReviewCliRequest
from munk.config.runtime import require_config_context
from munk.reviewing.models import ReviewCaseType, ReviewPlatform, ReviewRequest
from munk.services.machine_command_service import MachineCommandService


def review_command(
    *,
    app_id: str | None = None,
    change_summary: str | None = None,
    changed_files: list[str] | None = None,
    diff_text: str | None = None,
    requirement_doc: Path | None = None,
    technical_doc: Path | None = None,
    review_query: str | None = None,
    platform: list[str] | None = None,
    tag: list[str] | None = None,
    case_type: list[str] | None = None,
    artifact_path: Path | None = None,
    config: Path | None = None,
    request_file: Path | None = None,
    json_output: bool = False,
    wait: bool = True,
    detach: bool = False,
) -> None:
    try:
        reject_mixed_request_file_usage(
            request_file=request_file,
            command_name="review",
            allowed_mixed_keys={"config"},
            provided_business_args={
                "app_id": app_id,
                "change_summary": change_summary,
                "changed_files": changed_files,
                "diff_text": diff_text,
                "requirement_doc": requirement_doc,
                "technical_doc": technical_doc,
                "review_query": review_query,
                "platform": platform,
                "tag": tag,
                "case_type": case_type,
                "artifact_path": artifact_path,
                "config": config,
            },
        )
        if request_file is not None:
            request = load_json_request(request_file, ReviewCliRequest)
        else:
            request = ReviewRequest(
                app_id=app_id,
                change_summary=change_summary,
                changed_files=list(changed_files or []),
                diff_text=diff_text,
                requirement_doc_path=requirement_doc,
                technical_doc_path=technical_doc,
                review_query=review_query,
                platforms=cast(list[ReviewPlatform], list(platform or [])),
                tags=list(tag or []),
                case_types=cast(list[ReviewCaseType], list(case_type or [])),
                artifact_path=artifact_path,
            )
    except Exception as exc:
        handle_cli_error(command="review", exc=exc, json_output=json_output)

    resolved_config = require_config_context(
        cli_path=config,
        workspace_root=Path.cwd(),
        command_name="review",
    )

    response = MachineCommandService(resolved_config=resolved_config).submit_review(
        request=request,
        wait=wait,
        detach=detach,
        detached_argv=list(sys.argv[1:]),
    )
    if json_output:
        emit_json_response(response.payload)
        raise typer.Exit(code=response.exit_code)
    if response.payload["ok"] is False:
        typer.echo(response.payload["error"]["message"], err=True)
        raise typer.Exit(code=response.exit_code)

    data = response.payload["data"]
    typer.echo(f"operation_id={data['operation_id']}")
    typer.echo(f"operation_status={data['status']}")
    typer.echo(f"finding_count={data['finding_count']}")
    typer.echo(f"high_risk_count={data['high_risk_count']}")
    typer.echo(f"review_result_path={data['review_result_path']}")
    typer.echo(f"review_orchestration_path={data['review_orchestration_path']}")
    typer.echo(f"retrieval_path={data['retrieval_path']}")
    raise typer.Exit(code=response.exit_code)
