from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from munk.config import ResolvedConfig
from munk.execution.models import (
    CASE_EXECUTION_RESULT_SCHEMA_VERSION,
    CaseExecutionAttempt,
    CaseExecutionRequest,
    CaseExecutionResult,
    ExecutionOutcome,
)
from munk.services.artifact_manifest_models import ReproductionTargetKind
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.diagnostics_models import OperationDiagnostics
from munk.services.diagnostics_service import OperationDiagnosticsService
from munk.services.operations.service import OperationTracker
from munk.token_usage import merge_token_usages

from .models import CaseOrchestrationResult

ORCHESTRATION_DIAGNOSTICS_STAGE = "orchestration_engine"


@dataclass(frozen=True)
class MaterializedOrchestrationArtifacts:
    result: CaseExecutionResult
    diagnostics: OperationDiagnostics
    artifacts: dict[str, str]
    diagnostics_path: Path
    manifest_path: Path


class OrchestrationArtifactMaterializer:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        operation_tracker: OperationTracker | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._operation_tracker = operation_tracker
        self._artifact_manifest_service = ArtifactManifestService()
        self._diagnostics_service = OperationDiagnosticsService()

    def materialize(
        self,
        *,
        request: CaseExecutionRequest,
        orchestration_result: CaseOrchestrationResult,
        run_dir: Path,
    ) -> MaterializedOrchestrationArtifacts:
        run_dir.mkdir(parents=True, exist_ok=True)
        result_path = run_dir / "result.json"
        attempts_path = run_dir / "attempts.json"
        history_path = run_dir / "history.json"
        retry_handoffs_path = run_dir / "retry_handoffs.json"
        orchestration_result_path = run_dir / "orchestration_result.json"
        diagnostics_path = run_dir / "diagnostics.json"
        manifest_path = run_dir / "artifact_manifest.json"
        case_request_path = run_dir / "case.json"
        case_request_path.write_text(request.model_dump_json(indent=2), encoding="utf-8")

        attempts = [self._build_attempt(item) for item in orchestration_result.attempts]
        retry_handoffs = self._build_retry_handoffs(attempts)
        event_history = [
            entry.model_dump(mode="json") for entry in orchestration_result.history.entries
        ]
        final_attempt = attempts[-1]
        final_artifacts = self._build_artifacts(
            run_dir=run_dir,
            case_request_path=case_request_path,
            result_path=result_path,
            attempts_path=attempts_path,
            history_path=history_path,
            retry_handoffs_path=retry_handoffs_path,
            orchestration_result_path=orchestration_result_path,
            diagnostics_path=diagnostics_path,
            manifest_path=manifest_path,
            attempts=attempts,
        )
        result = CaseExecutionResult(
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case.case_id,
            run_dir=run_dir,
            status=orchestration_result.state.status,
            current_step=orchestration_result.state.current_step,
            final_decision=orchestration_result.final_decision.model_dump(mode="json"),
            execution=final_attempt.execution,
            verdict=final_attempt.verdict,
            summary=final_attempt.summary,
            judge_reason=final_attempt.judge_reason,
            failure_hypothesis=final_attempt.failure_hypothesis,
            confidence=final_attempt.confidence,
            missing_evidence=list(final_attempt.missing_evidence),
            supporting_evidence_ids=list(final_attempt.supporting_evidence_ids),
            evidence=list(final_attempt.evidence),
            attempt_count=len(attempts),
            attempts=attempts,
            event_history=event_history,
            supplemental_context=list(orchestration_result.state.supplemental_context),
            metadata=dict(orchestration_result.state.metadata),
            artifacts=final_artifacts,
            token_usage=orchestration_result.token_usage,
        )
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        attempts_path.write_text(
            "[" + ",\n".join(item.model_dump_json() for item in attempts) + "]\n" if attempts else "[]\n",
            encoding="utf-8",
        )
        history_path.write_text(orchestration_result.history.model_dump_json(indent=2), encoding="utf-8")
        retry_handoffs_path.write_text(json.dumps(retry_handoffs, indent=2) + "\n", encoding="utf-8")
        orchestration_result_path.write_text(orchestration_result.model_dump_json(indent=2), encoding="utf-8")
        operation_kind = self._operation_kind()
        manifest = self._artifact_manifest_service.build_case_manifest(
            run_dir=run_dir,
            artifacts=final_artifacts,
            case_id=request.case.case_id,
            title=request.case.title,
            verdict=result.verdict,
            execution_status=result.execution.status,
            operation_id=self._operation_id(),
            operation_kind=operation_kind,
            verification_verdict=result.verdict,
        )
        self._artifact_manifest_service.write_manifest(manifest_path, manifest)
        diagnostics = self._build_diagnostics(
            request=request,
            result=result,
            orchestration_result=orchestration_result,
            diagnostics_path=diagnostics_path,
            manifest_path=manifest_path,
        )
        self._diagnostics_service.write(diagnostics_path, diagnostics)
        return MaterializedOrchestrationArtifacts(
            result=result,
            diagnostics=diagnostics,
            artifacts=final_artifacts,
            diagnostics_path=diagnostics_path,
            manifest_path=manifest_path,
        )

    @staticmethod
    def _build_attempt(attempt_record: Any) -> CaseExecutionAttempt:
        runner = attempt_record.runner
        judge = attempt_record.judge
        execution = ExecutionOutcome(
            status=runner.status,
            stop_reason=runner.stop_reason,
            steps_completed=runner.steps_completed,
            error_message=runner.error_message,
            error_type=runner.error_type,
            last_action_summary=runner.last_action_summary,
            last_target_identity=runner.last_target_identity,
            last_surface_identity=runner.last_surface_identity,
        )
        return CaseExecutionAttempt(
            attempt_index=cast(int, attempt_record.attempt_index),
            runner_run_dir=runner.run_dir,
            execution=execution,
            verdict=judge.judge_result.verdict,
            summary=judge.judge_result.summary,
            judge_reason=judge.judge_result.reason,
            failure_hypothesis=judge.judge_result.failure_hypothesis,
            confidence=judge.judge_result.confidence,
            missing_evidence=list(judge.judge_result.missing_evidence),
            supporting_evidence_ids=list(judge.judge_result.supporting_evidence_ids),
            evidence=list(judge.judge_result.evidence),
            supplemental_context=list(judge.retry_guidance.supplemental_context),
            retry_reason=judge.retry_guidance.retry_reason,
            retry_handoff_message=getattr(attempt_record, "retry_handoff_message", None),
            decision=judge.decision.model_dump(mode="json"),
            artifacts={**runner.artifacts, **judge.artifacts},
            runner_usage=getattr(attempt_record, "runner_usage", None),
            judge_usage=getattr(attempt_record, "judge_usage", None),
            total_usage=getattr(
                attempt_record,
                "total_usage",
                merge_token_usages([getattr(runner, "token_usage", None), getattr(judge, "token_usage", None)]),
            ),
        )

    @staticmethod
    def _build_artifacts(
        *,
        run_dir: Path,
        case_request_path: Path,
        result_path: Path,
        attempts_path: Path,
        history_path: Path,
        retry_handoffs_path: Path,
        orchestration_result_path: Path,
        diagnostics_path: Path,
        manifest_path: Path,
        attempts: list[CaseExecutionAttempt],
    ) -> dict[str, str]:
        artifacts: "OrderedDict[str, str]" = OrderedDict(
            [
                ("case", str(case_request_path)),
                ("result", str(result_path)),
                ("attempts", str(attempts_path)),
                ("history", str(history_path)),
                ("retry_handoffs", str(retry_handoffs_path)),
                ("orchestration_result", str(orchestration_result_path)),
                ("diagnostics", str(diagnostics_path)),
                ("artifact_manifest", str(manifest_path)),
                ("orchestration_run_dir", str(run_dir)),
            ]
        )
        for attempt in attempts:
            prefix = f"attempt_{attempt.attempt_index}"
            artifacts[f"{prefix}_run_dir"] = str(attempt.runner_run_dir)
            for artifact_id, raw_path in attempt.artifacts.items():
                path = Path(raw_path)
                if path.exists():
                    artifacts[f"{prefix}_{artifact_id}"] = raw_path
        return dict(artifacts)

    @staticmethod
    def _build_retry_handoffs(attempts: list[CaseExecutionAttempt]) -> list[dict[str, object]]:
        handoffs: list[dict[str, object]] = []
        for attempt in attempts:
            message = (attempt.retry_handoff_message or "").strip()
            if not message:
                continue
            handoffs.append(
                {
                    "attempt_index": attempt.attempt_index,
                    "retry_attempt": attempt.attempt_index + 1,
                    "retry_reason": attempt.retry_reason,
                    "supplemental_context": list(attempt.supplemental_context),
                    "retry_handoff_message": message,
                }
            )
        return handoffs

    def _build_diagnostics(
        self,
        *,
        request: CaseExecutionRequest,
        result: CaseExecutionResult,
        orchestration_result: CaseOrchestrationResult,
        diagnostics_path: Path,
        manifest_path: Path,
    ) -> OperationDiagnostics:
        provider, model, role_models, config_fingerprint = self._diagnostics_service.resolve_provider_model(
            resolved_config=self._resolved_config,
            roles=("runner", "judge"),
        )
        artifact_checks = [
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="result",
                path=Path(result.artifacts["result"]),
                required_fields=("schema_version", "plan_id", "case_id", "attempt_count", "verdict"),
                expected_schema_version=CASE_EXECUTION_RESULT_SCHEMA_VERSION,
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="attempts",
                path=Path(result.artifacts["attempts"]),
                required=False,
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="history",
                path=Path(result.artifacts["history"]),
                required=False,
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="retry_handoffs",
                path=Path(result.artifacts["retry_handoffs"]),
                required=False,
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="orchestration_result",
                path=Path(result.artifacts["orchestration_result"]),
                required=False,
            ),
            self._diagnostics_service.build_path_artifact_check(
                artifact_id="artifact_manifest",
                path=manifest_path,
            ),
            self._diagnostics_service.build_path_artifact_check(
                artifact_id="diagnostics",
                path=diagnostics_path,
            ),
        ]
        final_judge_result = result.artifacts.get(f"attempt_{max(0, result.attempt_count - 1)}_judge_result")
        if final_judge_result:
            artifact_checks.append(
                self._diagnostics_service.build_json_artifact_check(
                    artifact_id="judge_result",
                    path=Path(final_judge_result),
                    required_fields=("verdict", "summary", "reason"),
                )
            )
        warning_summary: list[str] = []
        if result.execution.stop_reason:
            warning_summary.append(f"runner stop reason: {result.execution.stop_reason}")
        warning_summary.append(f"attempt count: {result.attempt_count}")
        return OperationDiagnostics(
            operation_id=self._operation_id(),
            operation_kind="run_case",
            app_id=request.app_id,
            status="succeeded",
            verification_verdict=result.verdict,
            started_at=orchestration_result.history.entries[0].timestamp if orchestration_result.history.entries else self._diagnostics_service.now_iso(),
            finished_at=self._diagnostics_service.now_iso(),
            duration_ms=0,
            provider=provider,
            model=model,
            role_models=role_models,
            config_fingerprint=config_fingerprint,
            device_ref=request.device_ref,
            entry_identity=result.execution.last_surface_identity or result.execution.last_target_identity,
            warning_summary=warning_summary,
            retry_count=max(0, result.attempt_count - 1),
            failure_stage=ORCHESTRATION_DIAGNOSTICS_STAGE if result.status == "escalated" else None,
            artifact_checks=artifact_checks,
            contract_versions={"case_execution_result": CASE_EXECUTION_RESULT_SCHEMA_VERSION},
            linked_operation_ids={},
        )

    def _operation_id(self) -> str | None:
        return self._operation_tracker.operation_id if self._operation_tracker is not None else None

    def _operation_kind(self) -> ReproductionTargetKind | None:
        if self._operation_tracker is None:
            return None
        kind = self._operation_tracker.get_record().kind
        if kind in {"plan", "run_case", "run_plan", "run_plans", "verify_change", "review"}:
            return cast(ReproductionTargetKind, kind)
        return None
