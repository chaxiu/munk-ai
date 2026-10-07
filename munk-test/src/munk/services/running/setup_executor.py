from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx
from httpx import URL

from munk.config.schema import HttpBaseConfig, TestEnvConfig
from munk.network.proxy import ResolvedProxyConfig, build_httpx_proxy_kwargs
from munk.services.errors import SetupExecutionError
from munk.testing import CommandSetupStep, HttpSetupStep, SetupStep, TestCase

_SETUP_HTTP_TIMEOUT_SEC = 30.0
_SETUP_COMMAND_TIMEOUT_SEC = 120.0
_DIAGNOSTIC_OUTPUT_LIMIT = 4000

SetupStepOutcome = Literal["succeeded", "failed"]


class SetupProgressEmitter(Protocol):
    def __call__(
        self,
        *,
        event_type: str,
        message: str,
        summary: str,
        data: dict[str, Any] | None = None,
    ) -> None: ...


@dataclass
class SetupStepDiagnostic:
    step_index: int
    step_total: int
    step_kind: str
    outcome: SetupStepOutcome = "succeeded"
    duration_ms: int = 0
    error_message: str | None = None
    method: str | None = None
    base: str | None = None
    path: str | None = None
    request_url: str | None = None
    request_body: object | None = None
    status_code: int | None = None
    expected_status: list[int] | None = None
    response_body: str | None = None
    exec: str | None = None
    args: list[str] = field(default_factory=list)
    exit_code: int | None = None
    expected_exit_code: int | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None


def execute_case_setup(
    *,
    case: TestCase,
    test_env: TestEnvConfig | None,
    run_dir: Path,
    proxy: ResolvedProxyConfig | None = None,
    emit_progress: SetupProgressEmitter | None = None,
) -> None:
    if not case.setup:
        return

    emit_progress = emit_progress or _noop_emit_progress
    step_total = len(case.setup)
    setup_started_at = time.monotonic()

    emit_progress(
        event_type="context_prepare_setup_started",
        message="context prepare setup started",
        summary="case setup started",
        data={"step_count": step_total},
    )

    for index, step in enumerate(case.setup):
        step_started_at = time.monotonic()
        diagnostic, error = _execute_setup_step_diagnostic(
            step=step,
            test_env=test_env,
            run_dir=run_dir,
            proxy=proxy,
            step_index=index,
            step_total=step_total,
        )
        diagnostic.duration_ms = max(0, int((time.monotonic() - step_started_at) * 1000))
        summary = _build_step_summary(diagnostic)
        emit_progress(
            event_type="context_prepare_setup_step",
            message=f"context prepare setup step {index + 1}/{step_total}: {summary}",
            summary=summary,
            data=_build_step_payload(diagnostic),
        )
        if error is not None:
            raise error

    setup_duration_ms = max(0, int((time.monotonic() - setup_started_at) * 1000))
    emit_progress(
        event_type="context_prepare_setup_ready",
        message="context prepare setup completed",
        summary="case setup completed",
        data={"step_count": step_total, "duration_ms": setup_duration_ms},
    )


def _execute_setup_step_diagnostic(
    *,
    step: SetupStep,
    test_env: TestEnvConfig | None,
    run_dir: Path,
    proxy: ResolvedProxyConfig | None,
    step_index: int,
    step_total: int,
) -> tuple[SetupStepDiagnostic, SetupExecutionError | None]:
    if isinstance(step, HttpSetupStep):
        return _execute_http_step_diagnostic(
            step=step,
            test_env=test_env,
            proxy=proxy,
            step_index=step_index,
            step_total=step_total,
        )
    if isinstance(step, CommandSetupStep):
        return _execute_command_step_diagnostic(
            step=step,
            test_env=test_env,
            run_dir=run_dir,
            step_index=step_index,
            step_total=step_total,
        )
    diagnostic = SetupStepDiagnostic(
        step_index=step_index,
        step_total=step_total,
        step_kind="unknown",
        outcome="failed",
        error_message=f"setup step {step_index + 1} has unsupported kind",
    )
    return diagnostic, SetupExecutionError(diagnostic.error_message)


def _execute_http_step_diagnostic(
    *,
    step: HttpSetupStep,
    test_env: TestEnvConfig | None,
    proxy: ResolvedProxyConfig | None,
    step_index: int,
    step_total: int,
) -> tuple[SetupStepDiagnostic, SetupExecutionError | None]:
    base_name = step.base.strip()
    diagnostic = SetupStepDiagnostic(
        step_index=step_index,
        step_total=step_total,
        step_kind="http",
        method=step.method,
        base=base_name or None,
        path=step.path,
        request_body=step.body,
        expected_status=list(step.expected_status),
    )

    if not base_name:
        diagnostic.outcome = "failed"
        diagnostic.error_message = f"setup step {step_index + 1} http.base must not be empty"
        return diagnostic, SetupExecutionError(diagnostic.error_message)

    try:
        base_config = _resolve_http_base(test_env=test_env, base_name=base_name, step_index=step_index)
    except SetupExecutionError as exc:
        diagnostic.outcome = "failed"
        diagnostic.error_message = str(exc)
        return diagnostic, exc

    request_url = _build_request_url(base_config.url, step.path)
    diagnostic.request_url = request_url
    headers = {**base_config.headers, **step.headers}

    request_kwargs: dict[str, object] = {
        "headers": headers,
    }
    if step.query:
        request_kwargs["params"] = step.query
    if step.body is not None and step.method in {"POST", "PUT", "PATCH"}:
        request_kwargs["json"] = step.body

    try:
        # Reuse Munk proxy helper: always trust_env=False; loopback hosts bypass
        # proxy by default; non-local bases may use config.proxy when enabled.
        with httpx.Client(
            timeout=_SETUP_HTTP_TIMEOUT_SEC,
            **build_httpx_proxy_kwargs(url=request_url, proxy=proxy),
        ) as client:
            response = client.request(
                step.method,
                request_url,
                **request_kwargs,
            )
    except Exception as exc:
        diagnostic.outcome = "failed"
        diagnostic.error_message = (
            f"case setup step {step_index + 1} (http) failed: {exc}"
        )
        error = SetupExecutionError(diagnostic.error_message)
        error.__cause__ = exc
        return diagnostic, error

    diagnostic.status_code = response.status_code
    diagnostic.response_body = _truncate_tail(response.text)

    if response.status_code not in step.expected_status:
        diagnostic.outcome = "failed"
        diagnostic.error_message = (
            f"setup step {step_index + 1} http {step.method} {request_url} "
            f"returned status {response.status_code}, expected {step.expected_status}; "
            f"body={diagnostic.response_body!r}"
        )
        return diagnostic, SetupExecutionError(diagnostic.error_message)

    return diagnostic, None


def _execute_command_step_diagnostic(
    *,
    step: CommandSetupStep,
    test_env: TestEnvConfig | None,
    run_dir: Path,
    step_index: int,
    step_total: int,
) -> tuple[SetupStepDiagnostic, SetupExecutionError | None]:
    executable = step.exec.strip()
    diagnostic = SetupStepDiagnostic(
        step_index=step_index,
        step_total=step_total,
        step_kind="command",
        exec=executable or None,
        args=list(step.args),
        expected_exit_code=step.expected_exit_code,
    )

    if not executable:
        diagnostic.outcome = "failed"
        diagnostic.error_message = f"setup step {step_index + 1} command.exec must not be empty"
        return diagnostic, SetupExecutionError(diagnostic.error_message)

    allowed_exec = _allowed_exec_set(test_env)
    if executable not in allowed_exec:
        diagnostic.outcome = "failed"
        diagnostic.error_message = (
            f"setup step {step_index + 1} command.exec '{executable}' is not in test_env.allowed_exec"
        )
        return diagnostic, SetupExecutionError(diagnostic.error_message)

    try:
        completed = subprocess.run(
            [executable, *step.args],
            shell=False,
            cwd=run_dir,
            capture_output=True,
            text=True,
            timeout=_SETUP_COMMAND_TIMEOUT_SEC,
            check=False,
        )
    except Exception as exc:
        diagnostic.outcome = "failed"
        diagnostic.error_message = (
            f"case setup step {step_index + 1} (command) failed: {exc}"
        )
        error = SetupExecutionError(diagnostic.error_message)
        error.__cause__ = exc
        return diagnostic, error

    diagnostic.exit_code = completed.returncode
    diagnostic.stdout_tail = _truncate_tail(completed.stdout)
    diagnostic.stderr_tail = _truncate_tail(completed.stderr)

    if completed.returncode != step.expected_exit_code:
        diagnostic.outcome = "failed"
        diagnostic.error_message = (
            f"setup step {step_index + 1} command '{executable}' "
            f"exited with {completed.returncode}, expected {step.expected_exit_code}; "
            f"stdout={diagnostic.stdout_tail!r}; stderr={diagnostic.stderr_tail!r}"
        )
        return diagnostic, SetupExecutionError(diagnostic.error_message)

    return diagnostic, None


def _build_step_payload(diagnostic: SetupStepDiagnostic) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "step_index": diagnostic.step_index,
        "step_total": diagnostic.step_total,
        "step_kind": diagnostic.step_kind,
        "outcome": diagnostic.outcome,
        "duration_ms": diagnostic.duration_ms,
    }
    if diagnostic.error_message is not None:
        payload["error_message"] = diagnostic.error_message
    if diagnostic.step_kind == "http":
        payload.update(
            {
                "method": diagnostic.method,
                "base": diagnostic.base,
                "path": diagnostic.path,
                "request_url": diagnostic.request_url,
                "request_body": diagnostic.request_body,
                "status_code": diagnostic.status_code,
                "expected_status": diagnostic.expected_status,
                "response_body": diagnostic.response_body,
            }
        )
    elif diagnostic.step_kind == "command":
        payload.update(
            {
                "exec": diagnostic.exec,
                "args": diagnostic.args,
                "exit_code": diagnostic.exit_code,
                "expected_exit_code": diagnostic.expected_exit_code,
                "stdout_tail": diagnostic.stdout_tail,
                "stderr_tail": diagnostic.stderr_tail,
            }
        )
    return payload


def _build_step_summary(diagnostic: SetupStepDiagnostic) -> str:
    failed_suffix = " (failed)" if diagnostic.outcome == "failed" else ""
    if diagnostic.step_kind == "http":
        status = diagnostic.status_code if diagnostic.status_code is not None else "?"
        return f"{diagnostic.method} {diagnostic.base} {diagnostic.path} → {status}{failed_suffix}"
    if diagnostic.step_kind == "command":
        exit_code = diagnostic.exit_code if diagnostic.exit_code is not None else "?"
        command_label = diagnostic.exec or "command"
        if diagnostic.args:
            command_label = f"{command_label} {' '.join(diagnostic.args)}"
        return f"{command_label} → exit {exit_code}{failed_suffix}"
    return f"setup step {diagnostic.step_index + 1}{failed_suffix}"


def _resolve_http_base(
    *,
    test_env: TestEnvConfig | None,
    base_name: str,
    step_index: int,
) -> HttpBaseConfig:
    if test_env is None or base_name not in test_env.bases:
        raise SetupExecutionError(
            f"setup step {step_index + 1} http.base '{base_name}' is not registered in test_env.bases"
        )
    base_config = test_env.bases[base_name]
    if not base_config.url.strip():
        raise SetupExecutionError(
            f"setup step {step_index + 1} http.base '{base_name}' has an empty url in config"
        )
    return base_config


def _allowed_exec_set(test_env: TestEnvConfig | None) -> set[str]:
    if test_env is None:
        return set()
    return {item.strip() for item in test_env.allowed_exec if item.strip()}


def _build_request_url(base_url: str, path: str) -> str:
    normalized_base = base_url.rstrip("/")
    if not path or path == "/":
        return f"{normalized_base}/"
    normalized_path = path if path.startswith("/") else f"/{path}"
    return str(URL(f"{normalized_base}/").join(normalized_path))


def _truncate_tail(value: str, limit: int = _DIAGNOSTIC_OUTPUT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return "...(truncated)\n" + value[-limit:]


def _noop_emit_progress(**_: object) -> None:
    return None
