from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from munk.config import ResolvedConfig
from munk.execution.models import CaseExecutionRequest, CaseExecutionResult, ExecutionOutcome
from munk.judging.models import JudgeEvidence, JudgeResult
from munk.judging.runtime import JudgeRuntime
from munk.running import RunnerRuntimeOutput
from munk.services.artifact_manifest_models import ReproductionTargetKind
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.diagnostics_models import OperationDiagnostics
from munk.services.diagnostics_service import OperationDiagnosticsService
from munk.services.events import RunEvent
from munk.services.judging import execute_case_judging
from munk.services.models import RunPaths
from munk.services.operations.service import OperationTracker

from .runtime_host import RunnerHostManagedPaths

RUNNER_RUNTIME_DIAGNOSTICS_STAGE = "runner_runtime"


@dataclass(frozen=True)
class MaterializedRunnerArtifacts:
    result: CaseExecutionResult
    diagnostics: OperationDiagnostics
    artifacts: dict[str, str]
    diagnostics_path: Path
    manifest_path: Path


class RunnerArtifactMaterializer:
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

    def materialize_success(
        self,
        *,
        request: CaseExecutionRequest,
        paths: RunPaths,
        host_paths: RunnerHostManagedPaths,
        runtime_output: RunnerRuntimeOutput,
        events: list[RunEvent],
        judge_runtime: JudgeRuntime | None,
    ) -> MaterializedRunnerArtifacts:
        result_data = runtime_output.result_data
        execution = ExecutionOutcome(
            status=result_data.status,
            stop_reason=result_data.stop_reason,
            steps_completed=result_data.steps_completed,
            last_action_summary=result_data.last_action_summary,
            last_target_identity=result_data.last_target_identity,
            last_surface_identity=result_data.last_surface_identity,
        )
        artifacts = self._build_artifacts(paths=paths, host_paths=host_paths, request=request)
        materialized_judge = execute_case_judging(
            request=request,
            execution=execution,
            events=list(events),
            artifacts=artifacts,
            resolved_config=self._resolved_config,
            tracker=cast(Any, self._operation_tracker),
            judge_runtime=judge_runtime,
        )
        artifacts.update(materialized_judge.artifacts)
        result = self._build_case_result(
            request=request,
            run_dir=paths.run_dir,
            execution=execution,
            judge_result=materialized_judge.result,
            artifacts=artifacts,
        )
        self._write_case_result(host_paths.result_path, result)
        manifest = self._build_case_manifest(result=result)
        self._artifact_manifest_service.write_manifest(host_paths.artifact_manifest_path, manifest)
        diagnostics = self._build_success_diagnostics(
            request=request,
            result=result,
            execution=execution,
            artifacts=artifacts,
            judge_result=materialized_judge.result,
            judge_diagnostics=materialized_judge.diagnostics,
        )
        self._diagnostics_service.write(host_paths.diagnostics_path, diagnostics)
        return MaterializedRunnerArtifacts(
            result=result,
            diagnostics=diagnostics,
            artifacts=artifacts,
            diagnostics_path=host_paths.diagnostics_path,
            manifest_path=host_paths.artifact_manifest_path,
        )

    def materialize_failure(
        self,
        *,
        request: CaseExecutionRequest,
        run_dir: Path,
        paths: RunPaths | None,
        host_paths: RunnerHostManagedPaths,
        events: list[RunEvent],
        exc: Exception,
        judge_runtime: JudgeRuntime | None,
        runtime_context_available: bool,
    ) -> MaterializedRunnerArtifacts:
        execution = ExecutionOutcome(
            status="failed",
            stop_reason="run_failed",
            steps_completed=0,
            error_message=str(exc),
            error_type=type(exc).__name__,
        )
        artifacts = self._build_artifacts(paths=paths, host_paths=host_paths, request=request, run_dir=run_dir)
        if runtime_context_available:
            materialized_judge = execute_case_judging(
                request=request,
                execution=execution,
                events=list(events),
                artifacts=artifacts,
                resolved_config=self._resolved_config,
                tracker=cast(Any, self._operation_tracker),
                judge_runtime=judge_runtime,
                raise_on_runtime_error=False,
            )
            judge_result = materialized_judge.result
            judge_diagnostics = materialized_judge.diagnostics
            artifacts.update(materialized_judge.artifacts)
        else:
            judge_result = self._build_fallback_judge_result(
                request=request,
                run_dir=run_dir,
                artifacts=artifacts,
                execution=execution,
            )
            judge_diagnostics = None
        result = self._build_case_result(
            request=request,
            run_dir=run_dir,
            execution=execution,
            judge_result=judge_result,
            artifacts=artifacts,
        )
        self._write_case_result(host_paths.result_path, result)
        manifest = self._build_case_manifest(result=result)
        self._artifact_manifest_service.write_manifest(host_paths.artifact_manifest_path, manifest)
        diagnostics = self._build_failure_diagnostics(
            request=request,
            result=result,
            execution=execution,
            artifacts=artifacts,
            judge_result=judge_result,
            judge_diagnostics=judge_diagnostics,
            exc=exc,
        )
        self._diagnostics_service.write(host_paths.diagnostics_path, diagnostics)
        return MaterializedRunnerArtifacts(
            result=result,
            diagnostics=diagnostics,
            artifacts=artifacts,
            diagnostics_path=host_paths.diagnostics_path,
            manifest_path=host_paths.artifact_manifest_path,
        )

    @staticmethod
    def _build_case_result(
        *,
        request: CaseExecutionRequest,
        run_dir: Path,
        execution: ExecutionOutcome,
        judge_result: JudgeResult,
        artifacts: dict[str, str],
    ) -> CaseExecutionResult:
        return CaseExecutionResult(
            plan_id=request.plan_id,
            case_id=request.case.case_id,
            run_dir=run_dir,
            execution=execution,
            verdict=judge_result.verdict,
            summary=judge_result.summary,
            judge_reason=judge_result.reason,
            failure_hypothesis=judge_result.failure_hypothesis,
            confidence=judge_result.confidence,
            missing_evidence=list(judge_result.missing_evidence),
            supporting_evidence_ids=list(judge_result.supporting_evidence_ids),
            evidence=[RunnerArtifactMaterializer._compact_evidence(item) for item in list(judge_result.evidence)],
            artifacts=artifacts,
        )

    @staticmethod
    def _compact_evidence(evidence: JudgeEvidence) -> JudgeEvidence:
        payload = dict(evidence.payload)
        compact_payload: dict[str, object] = {}
        path = payload.get("path")
        if isinstance(path, str):
            compact_payload["path"] = path
        step_index = payload.get("step_index")
        if isinstance(step_index, int):
            compact_payload["step_index"] = step_index
        excerpt = payload.get("excerpt")
        if excerpt is not None:
            compact_payload["excerpt"] = excerpt
        return JudgeEvidence(
            evidence_id=evidence.evidence_id,
            kind=evidence.kind,
            source=evidence.source,
            summary=evidence.summary,
            payload=compact_payload,
        )

    def _build_artifacts(
        self,
        *,
        host_paths: RunnerHostManagedPaths,
        request: CaseExecutionRequest,
        paths: RunPaths | None = None,
        run_dir: Path | None = None,
    ) -> dict[str, str]:
        effective_run_dir = run_dir or host_paths.root_dir
        artifacts: dict[str, str] = {
            "case": str(paths.case_path if paths is not None and paths.case_path is not None else effective_run_dir / "case.json"),
            "result": str(host_paths.result_path),
            "artifact_manifest": str(host_paths.artifact_manifest_path),
            "diagnostics": str(host_paths.diagnostics_path),
        }
        if paths is not None:
            artifacts["log"] = str(paths.log_path)
            optional_paths = {
                "decision_trace": paths.decision_trace_path,
                "runner_history": paths.runner_history_path,
                "runner_memory": paths.runner_memory_path,
                "context_prep": paths.context_prep_path,
                "runtime_logs": paths.runtime_logs_dir,
                "raw_screenshots": paths.raw_dir,
                "annotated_screenshots": paths.annotated_dir,
                "observation_frames": paths.observation_frames_dir,
                "observation_diffs": paths.observation_diffs_dir,
                "observation_tree": paths.observation_tree_dir,
                "llm_transcript": paths.llm_transcript_path if paths.llm_transcript_path and paths.llm_transcript_path.exists() else None,
            }
            for artifact_id, path in optional_paths.items():
                if path is not None:
                    artifacts[artifact_id] = str(path)
        if request.artifact_path is not None:
            artifacts["input_artifact"] = str(request.artifact_path)
        return artifacts

    def _build_success_diagnostics(
        self,
        *,
        request: CaseExecutionRequest,
        result: CaseExecutionResult,
        execution: ExecutionOutcome,
        artifacts: dict[str, str],
        judge_result: JudgeResult,
        judge_diagnostics: OperationDiagnostics,
    ) -> OperationDiagnostics:
        provider, model, role_models, config_fingerprint = self._diagnostics_service.resolve_provider_model(
            resolved_config=self._resolved_config,
            roles=("runner", "judge"),
        )
        warning_summary = list(judge_diagnostics.warning_summary)
        if execution.stop_reason:
            warning_summary.append(f"runner stop reason: {execution.stop_reason}")
        return OperationDiagnostics(
            operation_id=self._operation_id(),
            operation_kind="run_case",
            app_id=request.app_id,
            status="succeeded",
            verification_verdict=result.verdict,
            started_at=judge_diagnostics.started_at,
            finished_at=self._diagnostics_service.now_iso(),
            duration_ms=judge_diagnostics.duration_ms,
            provider=provider,
            model=model,
            role_models=role_models,
            config_fingerprint=config_fingerprint,
            device_ref=request.device_ref,
            entry_identity=execution.last_surface_identity or execution.last_target_identity,
            warning_summary=warning_summary,
            artifact_checks=self._build_artifact_checks(artifacts),
            contract_versions={},
            linked_operation_ids={},
        )

    def _build_failure_diagnostics(
        self,
        *,
        request: CaseExecutionRequest,
        result: CaseExecutionResult,
        execution: ExecutionOutcome,
        artifacts: dict[str, str],
        judge_result: JudgeResult,
        judge_diagnostics: OperationDiagnostics | None,
        exc: Exception,
    ) -> OperationDiagnostics:
        provider, model, role_models, config_fingerprint = self._diagnostics_service.resolve_provider_model(
            resolved_config=self._resolved_config,
            roles=("runner", "judge"),
        )
        warning_summary = list(judge_diagnostics.warning_summary) if judge_diagnostics is not None else []
        if execution.stop_reason:
            warning_summary.append(f"runner stop reason: {execution.stop_reason}")
        return OperationDiagnostics(
            operation_id=self._operation_id(),
            operation_kind="run_case",
            app_id=request.app_id,
            status="failed",
            verification_verdict=result.verdict,
            started_at=judge_diagnostics.started_at if judge_diagnostics is not None else self._diagnostics_service.now_iso(),
            finished_at=self._diagnostics_service.now_iso(),
            duration_ms=judge_diagnostics.duration_ms if judge_diagnostics is not None else 0,
            provider=provider,
            model=model,
            role_models=role_models,
            config_fingerprint=config_fingerprint,
            device_ref=request.device_ref,
            entry_identity=execution.last_surface_identity or execution.last_target_identity,
            warning_summary=warning_summary,
            failure_category=self._diagnostics_service.classify_exception(exc),
            failure_stage=RUNNER_RUNTIME_DIAGNOSTICS_STAGE,
            failure_message=str(exc),
            artifact_checks=self._build_artifact_checks(artifacts),
            contract_versions={},
            linked_operation_ids={},
        )

    def _build_artifact_checks(self, artifacts: dict[str, str]) -> list:
        checks = [
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="case",
                path=Path(artifacts["case"]),
                required_fields=("app_id", "plan_id", "case"),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="result",
                path=Path(artifacts["result"]),
                required_fields=("plan_id", "case_id", "execution", "verdict", "artifacts"),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="artifact_manifest",
                path=Path(artifacts["artifact_manifest"]),
                required_fields=("root_dir", "primary_artifacts", "case_runs"),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="judge_result",
                path=judge_path(artifacts.get("judge_result")),
                required_fields=("verdict", "summary", "reason"),
                required=False,
            ),
        ]
        for artifact_id in (
            "decision_trace",
            "runner_history",
            "runner_memory",
            "llm_transcript",
            "runtime_logs",
            "observation_frames",
            "observation_diffs",
            "observation_tree",
        ):
            raw_path = artifacts.get(artifact_id)
            if raw_path is None:
                continue
            checks.append(
                self._diagnostics_service.build_path_artifact_check(
                    artifact_id=artifact_id,
                    path=Path(raw_path),
                    required=False,
                )
            )
        return checks

    def _build_case_manifest(self, *, result: CaseExecutionResult):
        return self._artifact_manifest_service.build_case_manifest(
            run_dir=result.run_dir,
            artifacts=result.artifacts,
            case_id=result.case_id,
            title=result.summary or result.case_id,
            verdict=result.verdict,
            execution_status=result.execution.status,
            operation_id=self._operation_id(),
            operation_kind=self._operation_kind(),
            verification_verdict=result.verdict,
        )

    @staticmethod
    def _write_case_result(path: Path, result: CaseExecutionResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    def _build_fallback_judge_result(
        self,
        *,
        request: CaseExecutionRequest,
        run_dir: Path,
        artifacts: dict[str, str],
        execution: ExecutionOutcome,
    ) -> JudgeResult:
        return JudgeResult(
            verdict="failed",
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case.case_id,
            operation_id=self._operation_id(),
            summary=request.case.title,
            reason=execution.error_message or execution.stop_reason or "execution failed",
            failure_hypothesis="runner execution failed before case completion",
            missing_evidence=[],
            supporting_evidence_ids=["execution"],
            evidence=[],
            judge_request_path=run_dir / "judge_request.json",
            judge_result_path=run_dir / "judge_result.json",
            diagnostics_path=Path(artifacts["diagnostics"]),
            llm_transcript_path=Path(artifacts["llm_transcript"]) if "llm_transcript" in artifacts else None,
        )

    def _operation_id(self) -> str | None:
        tracker = self._operation_tracker
        if tracker is None:
            return None
        try:
            record = tracker.get_record()
            return getattr(record, "operation_id", None)
        except Exception:
            return getattr(tracker, "operation_id", None)

    def _operation_kind(self) -> ReproductionTargetKind | None:
        tracker = self._operation_tracker
        if tracker is None:
            return None
        try:
            record = tracker.get_record()
            return getattr(record, "kind", None)
        except Exception:
            return getattr(tracker, "kind", None)


def judge_path(raw_path: str | None) -> Path:
    return Path(raw_path) if raw_path else Path("/__missing__/judge_result.json")
