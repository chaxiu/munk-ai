from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

import typer
from pydantic import BaseModel, ValidationError

from munk.services.machine_contracts import (
    InvalidMachineRequestError,
    build_error_result,
    classify_exception,
)
from munk.services.machine_contracts import (
    build_success_response as contract_build_success_response,
)

ERROR_OPERATION_CANCELLED = "operation_cancelled"
ModelT = TypeVar("ModelT", bound=BaseModel)



def load_json_request(path: Path, model_type: type[ModelT]) -> ModelT:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InvalidMachineRequestError(f"request file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InvalidMachineRequestError(f"request file is not valid JSON: {exc}") from exc
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        raise InvalidMachineRequestError(f"request file validation failed: {exc}") from exc


def reject_mixed_request_file_usage(
    *,
    request_file: Path | None,
    command_name: str,
    provided_business_args: dict[str, Any],
    allowed_mixed_keys: set[str] | None = None,
) -> None:
    if request_file is None:
        return
    allowed_mixed_keys = allowed_mixed_keys or set()
    mixed_keys = sorted(
        key
        for key, value in provided_business_args.items()
        if key not in allowed_mixed_keys and value is not None and value != []
    )
    if mixed_keys:
        joined = ", ".join(mixed_keys)
        raise InvalidMachineRequestError(
            f"{command_name} does not allow mixing --request-file with command arguments: {joined}"
        )

def build_success_response(
    *,
    command: str,
    data: dict[str, Any],
    artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return contract_build_success_response(command=command, data=data, artifacts=artifacts)


def build_error_response(
    *,
    command: str,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_error_result(
        command=command,
        exc=InvalidMachineRequestError(message),
        details=details,
    ).payload
    payload["error"]["code"] = code
    return payload


def emit_json_response(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def handle_cli_error(*, command: str, exc: Exception, json_output: bool) -> None:
    exit_code, error_code = classify_exception(exc)
    if json_output:
        emit_json_response(build_error_result(command=command, exc=exc).payload)
    else:
        typer.echo(str(exc), err=True)
    raise typer.Exit(code=exit_code) from exc
