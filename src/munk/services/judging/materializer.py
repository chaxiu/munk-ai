from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from munk.config import ResolvedConfig
from munk.judging.models import (
    JUDGE_RESULT_SCHEMA_VERSION,
    JudgeExecutionSummary,
    JudgeRequest,
    JudgeResult,
    JudgeRuntimeContext,
    JudgeRuntimeOutput,
)
from munk.services.diagnostics_models import OperationDiagnostics
from munk.services.diagnostics_service import OperationDiagnosticsService

from .runtime_host import JudgeHostManagedPaths

JUDGE_RUNTIME_DIAGNOSTICS_STAGE = "judge_runtime"


@dataclass(frozen=True)
class MaterializedJudgeArtifacts:
    result: JudgeResult
    diagnostics: OperationDiagnostics
    judge_request_path: Path
    judge_prompt_path: Path
    judge_tool_calls_path: Path
    judge_evidence_selection_path: Path
    judge_llm_transcript_path: Path | None = None

    @property
    def artifacts(self) -> dict[str, str]:
        artifacts: dict[str, str] = {
            "judge_result": str(self.result.judge_result_path),
        }
        if self.result.diagnostics_path is not None:
            artifacts["diagnostics"] = str(self.result.diagnostics_path)
        optional_paths = {
            "judge_request": self.judge_request_path,
            "judge_prompt": self.judge_prompt_path,
            "judge_tool_calls": self.judge_tool_calls_path,
            "judge_evidence_selection": self.judge_evidence_selection_path,
            "judge_llm_transcript": self.judge_llm_transcript_path,
        }
        for artifact_id, path in optional_paths.items():
            if path is not None and path.exists():
                artifacts[artifact_id] = str(path)
        return artifacts


class JudgeArtifactMaterializer:
    def __init__(self, *, resolved_config: ResolvedConfig) -> None:
        self._resolved_config = resolved_config
        self._diagnostics_service = OperationDiagnosticsService()

    def materialize_success(
        self,
        *,
        runtime_output: JudgeRuntimeOutput,
        request: JudgeRequest,
        context: JudgeRuntimeContext,
        host_paths: JudgeHostManagedPaths,
        runtime_id: str | None,
    ) -> MaterializedJudgeArtifacts:
        result = JudgeResult(
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            operation_id=context.operation_id,
            verdict=runtime_output.result_data.verdict,
            summary=runtime_output.result_data.summary,
            reason=runtime_output.result_data.reason,
            failure_hypothesis=runtime_output.result_data.failure_hypothesis,
            confidence=runtime_output.result_data.confidence,
            missing_evidence=list(runtime_output.result_data.missing_evidence),
            supporting_evidence_ids=list(runtime_output.result_data.supporting_evidence_ids),
            evidence=list(runtime_output.result_data.evidence),
            needs_optimization=runtime_output.result_data.needs_optimization,
            optimization_fields=list(runtime_output.result_data.optimization_fields),
            optimization_reason=runtime_output.result_data.optimization_reason,
            optimization_confidence=runtime_output.result_data.optimization_confidence,
            judge_request_path=context.managed_paths.judge_request_path,
            judge_result_path=host_paths.judge_result_path,
            diagnostics_path=host_paths.diagnostics_path,
            llm_transcript_path=context.managed_paths.llm_transcript_path,
            token_usage=runtime_output.token_usage,
        )
        self._write_result(host_paths.judge_result_path, result)
        diagnostics = self._build_diagnostics(
            request=request,
            result=result,
            execution=request.execution,
            started_at=runtime_output.started_at,
            duration_ms=runtime_output.duration_ms,
            warning_summary=list(runtime_output.warning_summary),
            tool_calls=list(runtime_output.tool_calls),
            runtime_id=runtime_id,
            failure_message=None,
            status="succeeded",
        )
        self._diagnostics_service.write(host_paths.diagnostics_path, diagnostics)
        return MaterializedJudgeArtifacts(
            result=result,
            diagnostics=diagnostics,
            judge_request_path=context.managed_paths.judge_request_path,
            judge_prompt_path=context.managed_paths.judge_prompt_path,
            judge_tool_calls_path=context.managed_paths.tool_calls_path,
            judge_evidence_selection_path=context.managed_paths.evidence_selection_path,
            judge_llm_transcript_path=context.managed_paths.llm_transcript_path,
        )

    def materialize_failure(
        self,
        *,
        request: JudgeRequest,
        context: JudgeRuntimeContext,
        host_paths: JudgeHostManagedPaths,
        execution: JudgeExecutionSummary,
        exc: Exception,
        runtime_id: str | None,
    ) -> MaterializedJudgeArtifacts:
        if not context.managed_paths.judge_request_path.exists():
            context.managed_paths.judge_request_path.write_text(
                request.model_dump_json(indent=2),
                encoding="utf-8",
            )
        result = JudgeResult(
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            operation_id=context.operation_id,
            verdict="failed",
            summary=request.case_title,
            reason=str(exc) or execution.error_message or execution.stop_reason or "judge runtime failed",
            failure_hypothesis="judge runtime failed before producing a structured verdict",
            missing_evidence=[],
            supporting_evidence_ids=["execution"],
            evidence=[],
            judge_request_path=context.managed_paths.judge_request_path,
            judge_result_path=host_paths.judge_result_path,
            diagnostics_path=host_paths.diagnostics_path,
            llm_transcript_path=context.managed_paths.llm_transcript_path,
            token_usage=None,
        )
        self._write_result(host_paths.judge_result_path, result)
        diagnostics = self._build_diagnostics(
            request=request,
            result=result,
            execution=execution,
            started_at=self._diagnostics_service.now_iso(),
            duration_ms=0,
            warning_summary=[],
            tool_calls=self._load_tool_calls(context.managed_paths.tool_calls_path),
            runtime_id=runtime_id,
            failure_exc=exc,
            failure_message=str(exc),
            status="failed",
        )
        self._diagnostics_service.write(host_paths.diagnostics_path, diagnostics)
        return MaterializedJudgeArtifacts(
            result=result,
            diagnostics=diagnostics,
            judge_request_path=context.managed_paths.judge_request_path,
            judge_prompt_path=context.managed_paths.judge_prompt_path,
            judge_tool_calls_path=context.managed_paths.tool_calls_path,
            judge_evidence_selection_path=context.managed_paths.evidence_selection_path,
            judge_llm_transcript_path=context.managed_paths.llm_transcript_path,
        )

    def _build_diagnostics(
        self,
        *,
        request: JudgeRequest,
        result: JudgeResult,
        execution: JudgeExecutionSummary,
        started_at: str,
        duration_ms: int,
        warning_summary: list[str],
        tool_calls: list[str],
        runtime_id: str | None,
        failure_exc: Exception | None = None,
        failure_message: str | None,
        status: Literal["succeeded", "failed"],
    ) -> OperationDiagnostics:
        provider, model, role_models, config_fingerprint = self._diagnostics_service.resolve_provider_model(
            resolved_config=self._resolved_config,
            roles=("judge",),
        )
        artifact_checks = [
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="judge_request",
                path=result.judge_request_path,
                required_fields=("app_id", "plan_id", "case_id", "intent", "expected"),
            ),
            self._diagnostics_service.build_path_artifact_check(
                artifact_id="judge_prompt",
                path=result.judge_result_path.parent / "judge_prompt.txt",
                required=False,
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="judge_tool_calls",
                path=result.judge_result_path.parent / "judge_tool_calls.json",
                required_fields=("tool_calls",),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="judge_evidence_selection",
                path=result.judge_result_path.parent / "judge_evidence_selection.json",
                required_fields=("mode",),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="judge_result",
                path=result.judge_result_path,
                required_fields=("verdict", "summary", "reason"),
                expected_schema_version=JUDGE_RESULT_SCHEMA_VERSION,
            ),
        ]
        if result.llm_transcript_path is not None:
            artifact_checks.append(
                self._diagnostics_service.build_path_artifact_check(
                    artifact_id="judge_llm_transcript",
                    path=result.llm_transcript_path,
                    required=False,
                )
            )
        warning_items = list(warning_summary)
        if runtime_id:
            warning_items.append(f"judge runtime: {runtime_id}")
        if tool_calls:
            warning_items.append(f"judge tool calls: {len(tool_calls)}")
        return OperationDiagnostics(
            operation_id=result.operation_id,
            operation_kind="run_case",
            app_id=request.app_id,
            status=cast(Literal["succeeded", "failed"], status),
            verification_verdict=result.verdict,
            started_at=started_at,
            finished_at=self._diagnostics_service.now_iso(),
            duration_ms=duration_ms,
            provider=provider,
            model=model,
            role_models=role_models,
            config_fingerprint=config_fingerprint,
            warning_summary=warning_items,
            failure_category=self._diagnostics_service.classify_exception(failure_exc)
            if failure_exc is not None
            else None,
            failure_stage=JUDGE_RUNTIME_DIAGNOSTICS_STAGE if failure_message else None,
            failure_message=failure_message,
            artifact_checks=artifact_checks,
            contract_versions={
                "judge_result": result.schema_version,
            },
            linked_operation_ids={},
            device_ref=None,
            entry_identity=execution.last_surface_identity or execution.last_target_identity,
        )

    @staticmethod
    def _load_tool_calls(path: Path) -> list[str]:
        if not path.exists():
            return []
        try:
            payload = path.read_text(encoding="utf-8")
        except OSError:
            return []
        try:
            import json

            data = json.loads(payload)
        except Exception:  # noqa: BLE001
            return []
        tool_calls = data.get("tool_calls")
        if not isinstance(tool_calls, list):
            return []
        return [str(item) for item in tool_calls]

    @staticmethod
    def _write_result(path: Path, result: JudgeResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
