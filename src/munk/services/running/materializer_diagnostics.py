from __future__ import annotations

from pathlib import Path

from munk.artifacts import (
    ARTIFACT_ID_ARTIFACT_MANIFEST,
    ARTIFACT_ID_CASE,
    ARTIFACT_ID_DECISION_TRACE,
    ARTIFACT_ID_LLM_TRANSCRIPT,
    ARTIFACT_ID_OBSERVATION_DIFFS,
    ARTIFACT_ID_OBSERVATION_FRAMES,
    ARTIFACT_ID_OBSERVATION_TREE,
    ARTIFACT_ID_RESULT,
    ARTIFACT_ID_RUNNER_HISTORY,
    ARTIFACT_ID_RUNNER_MEMORY,
    ARTIFACT_ID_RUNTIME_LOGS,
)
from munk.config import ResolvedConfig
from munk.execution.models import CaseExecutionRequest, CaseExecutionResult, ExecutionOutcome
from munk.services.diagnostics_models import OperationDiagnostics
from munk.services.diagnostics_service import OperationDiagnosticsService

RUNNER_RUNTIME_DIAGNOSTICS_STAGE = "runner_runtime"


def build_runner_success_diagnostics(
    *,
    diagnostics_service: OperationDiagnosticsService,
    resolved_config: ResolvedConfig,
    operation_id: str | None,
    request: CaseExecutionRequest,
    result: CaseExecutionResult,
    execution: ExecutionOutcome,
    artifacts: dict[str, str],
    judge_diagnostics: OperationDiagnostics,
) -> OperationDiagnostics:
    provider, model, role_models, config_fingerprint = diagnostics_service.resolve_provider_model(
        resolved_config=resolved_config,
        roles=("runner", "judge"),
    )
    warning_summary = list(judge_diagnostics.warning_summary)
    if execution.stop_reason:
        warning_summary.append(f"runner stop reason: {execution.stop_reason}")
    return OperationDiagnostics(
        operation_id=operation_id,
        operation_kind="run_case",
        app_id=request.app_id,
        status="succeeded",
        verification_verdict=result.verdict,
        started_at=judge_diagnostics.started_at,
        finished_at=diagnostics_service.now_iso(),
        duration_ms=judge_diagnostics.duration_ms,
        provider=provider,
        model=model,
        role_models=role_models,
        config_fingerprint=config_fingerprint,
        device_ref=request.device_ref,
        entry_identity=execution.last_surface_identity or execution.last_target_identity,
        warning_summary=warning_summary,
        artifact_checks=build_runner_artifact_checks(diagnostics_service=diagnostics_service, artifacts=artifacts),
        contract_versions={},
        linked_operation_ids={},
    )


def build_runner_failure_diagnostics(
    *,
    diagnostics_service: OperationDiagnosticsService,
    resolved_config: ResolvedConfig,
    operation_id: str | None,
    request: CaseExecutionRequest,
    result: CaseExecutionResult,
    execution: ExecutionOutcome,
    artifacts: dict[str, str],
    judge_diagnostics: OperationDiagnostics | None,
    exc: Exception,
) -> OperationDiagnostics:
    provider, model, role_models, config_fingerprint = diagnostics_service.resolve_provider_model(
        resolved_config=resolved_config,
        roles=("runner", "judge"),
    )
    warning_summary = list(judge_diagnostics.warning_summary) if judge_diagnostics is not None else []
    if execution.stop_reason:
        warning_summary.append(f"runner stop reason: {execution.stop_reason}")
    return OperationDiagnostics(
        operation_id=operation_id,
        operation_kind="run_case",
        app_id=request.app_id,
        status="failed",
        verification_verdict=result.verdict,
        started_at=judge_diagnostics.started_at if judge_diagnostics is not None else diagnostics_service.now_iso(),
        finished_at=diagnostics_service.now_iso(),
        duration_ms=judge_diagnostics.duration_ms if judge_diagnostics is not None else 0,
        provider=provider,
        model=model,
        role_models=role_models,
        config_fingerprint=config_fingerprint,
        device_ref=request.device_ref,
        entry_identity=execution.last_surface_identity or execution.last_target_identity,
        warning_summary=warning_summary,
        failure_category=diagnostics_service.classify_exception(exc),
        failure_stage=RUNNER_RUNTIME_DIAGNOSTICS_STAGE,
        failure_message=str(exc),
        artifact_checks=build_runner_artifact_checks(diagnostics_service=diagnostics_service, artifacts=artifacts),
        contract_versions={},
        linked_operation_ids={},
    )


def build_runner_artifact_checks(
    *,
    diagnostics_service: OperationDiagnosticsService,
    artifacts: dict[str, str],
) -> list:
    checks = [
        diagnostics_service.build_json_artifact_check(
            artifact_id=ARTIFACT_ID_CASE,
            path=Path(artifacts[ARTIFACT_ID_CASE]),
            required_fields=("app_id", "plan_id", "case"),
        ),
        diagnostics_service.build_json_artifact_check(
            artifact_id=ARTIFACT_ID_RESULT,
            path=Path(artifacts[ARTIFACT_ID_RESULT]),
            required_fields=("plan_id", "case_id", "execution", "verdict", "artifacts"),
        ),
        diagnostics_service.build_json_artifact_check(
            artifact_id=ARTIFACT_ID_ARTIFACT_MANIFEST,
            path=Path(artifacts[ARTIFACT_ID_ARTIFACT_MANIFEST]),
            required_fields=("root_dir", "primary_artifacts", "case_runs"),
        ),
        diagnostics_service.build_json_artifact_check(
            artifact_id="judge_result",
            path=judge_path(artifacts.get("judge_result")),
            required_fields=("verdict", "summary", "reason"),
            required=False,
        ),
    ]
    for artifact_id in (
        ARTIFACT_ID_DECISION_TRACE,
        ARTIFACT_ID_RUNNER_HISTORY,
        ARTIFACT_ID_RUNNER_MEMORY,
        ARTIFACT_ID_LLM_TRANSCRIPT,
        ARTIFACT_ID_RUNTIME_LOGS,
        ARTIFACT_ID_OBSERVATION_FRAMES,
        ARTIFACT_ID_OBSERVATION_DIFFS,
        ARTIFACT_ID_OBSERVATION_TREE,
        "ios_bridge",
        "ios_bridge_session",
        "ios_bridge_events",
        "ios_bridge_summary",
    ):
        raw_path = artifacts.get(artifact_id)
        if raw_path is None:
            continue
        checks.append(
            diagnostics_service.build_path_artifact_check(
                artifact_id=artifact_id,
                path=Path(raw_path),
                required=False,
            )
        )
    return checks


def judge_path(raw_path: str | None) -> Path:
    return Path(raw_path) if raw_path else Path("/__missing__/judge_result.json")
