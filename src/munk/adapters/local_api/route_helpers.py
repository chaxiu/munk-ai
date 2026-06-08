from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import cast
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import iterate_in_threadpool

from munk.adapters.local_api.artifact_readers import (
    ArtifactChildrenUnsupportedError,
    ArtifactManifestNotFoundError,
    ArtifactNotFoundError,
    ArtifactPreviewUnsupportedError,
)
from munk.adapters.shared.operation_presenters import build_operation_summary
from munk.adapters.shared.payload_models import OperationSummaryData
from munk.services.errors import OperationNotFoundError
from munk.services.machine_contracts import MachineCommandResponse
from munk.services.operations.models import OperationRecord
from munk.user_data import operations_home

_logger = logging.getLogger(__name__)


def machine_route_response(
    response: Response,
    command_response: MachineCommandResponse,
) -> dict[str, object] | JSONResponse:
    payload = cast(dict[str, object], command_response.payload)
    if payload.get("ok") is True:
        response.status_code = command_response.http_status
        return payload
    return JSONResponse(status_code=command_response.http_status, content=payload)


def json_response(response: MachineCommandResponse) -> JSONResponse:
    return JSONResponse(status_code=response.http_status, content=response.payload)


def operation_summary_payload(record: OperationRecord) -> OperationSummaryData:
    return build_operation_summary(record)


def error_payload(
    *,
    command: str,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": False,
        "command": command,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        error = cast(dict[str, object], payload["error"])
        error["details"] = details
    return payload


def error_response(
    *,
    status_code: int,
    command: str,
    code: str,
    message: str,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_payload(
            command=command,
            code=code,
            message=message,
            details=details,
        ),
    )


def artifact_error_response(*, command: str, exc: Exception) -> JSONResponse:
    if isinstance(exc, (OperationNotFoundError, ArtifactManifestNotFoundError, ArtifactNotFoundError)):
        status_code = 404
    elif isinstance(exc, (ArtifactPreviewUnsupportedError, ArtifactChildrenUnsupportedError)):
        status_code = 400
    else:
        status_code = 500
    code = getattr(exc, "code", "artifact_route_failed")
    return error_response(
        status_code=status_code,
        command=command,
        code=code,
        message=str(exc),
    )


def log_500_response(request: Request, response: Response, body_preview: str) -> None:
    _logger.error(
        "local api 500 response: method=%s path=%s query=%s status=%s body=%s",
        request.method,
        request.url.path,
        request.url.query or "-",
        response.status_code,
        body_preview,
    )


async def response_body_preview(response: Response) -> str:
    body = getattr(response, "body", b"")
    if not body:
        body_iterator = getattr(response, "body_iterator", None)
        if body_iterator is not None:
            chunks: list[bytes] = []
            async for chunk in body_iterator:
                if isinstance(chunk, bytes):
                    chunks.append(chunk)
                else:
                    chunks.append(chunk.encode("utf-8"))
            body = b"".join(chunks)
            setattr(response, "body_iterator", iterate_in_threadpool(iter([body])))
    if isinstance(body, bytes):
        text = body.decode("utf-8", errors="replace")
    elif isinstance(body, str):
        text = body
    else:
        text = ""
    text = text.strip()
    if not text:
        return "<empty>"
    if len(text) > 4000:
        return f"{text[:4000]}...(truncated)"
    return text


def build_submit_argv(command: str, payload: dict[str, object]) -> list[str]:
    request_file = write_request_payload(command, payload)
    if command == "plan":
        return ["plan", "--request-file", str(request_file), "--json"]
    if command == "run_case":
        return ["run", "case", "--request-file", str(request_file), "--json"]
    if command == "run_plan":
        return ["run", "plan", "--request-file", str(request_file), "--json"]
    if command == "run_plans":
        return ["run", "plans", "--request-file", str(request_file), "--json"]
    if command == "verify_change":
        return ["verify", "change", "--request-file", str(request_file), "--json"]
    if command == "review":
        return ["review", "--request-file", str(request_file), "--json"]
    raise ValueError(f"unsupported local api command: {command}")


def write_request_payload(command: str, payload: dict[str, object]) -> Path:
    request_dir = operations_home() / "http_requests"
    request_dir.mkdir(parents=True, exist_ok=True)
    path = request_dir / f"{command}_{uuid4().hex}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
