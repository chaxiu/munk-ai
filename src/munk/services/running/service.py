from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from munk.agent_base.llm import llm_transcript_observer_scope
from munk.artifacts import (
    ARTIFACT_ID_ARTIFACT_MANIFEST,
    ARTIFACT_ID_DIAGNOSTICS,
)
from munk.config import ResolvedConfig, resolve_orchestration_policy
from munk.device import SupportsClose
from munk.execution.models import CaseExecutionRequest, CaseExecutionResult, ExecutionOutcome
from munk.running import RunnerRuntimeOutput, create_runner_runtime
from munk.services.events import (
    RunEvent,
    RunEventSink,
    RunEventType,
    RunFailedEvent,
    RunStartedEvent,
    build_run_failed_event_payload,
    build_run_started_event_payload,
    with_run_event_context,
)
from munk.services.judge_runtime import resolve_judge_runtime
from munk.services.logging_service import setup_logging
from munk.services.models import RunPaths, RunStatus
from munk.services.operations.active_device_leases import unbind_operation_device
from munk.services.operations.llm_timeline import build_llm_timeline_observer
from munk.services.operations.service import OperationTracker
from munk.services.orchestration import CaseOrchestrationRequest, DeterministicOrchestrationEngine
from munk.services.orchestration.materializer import OrchestrationArtifactMaterializer
from munk.services.running.execution_session import RunExecutionSession
from munk.services.running.materializer import RunnerArtifactMaterializer
from munk.services.running.paths import prepare_run_paths
from munk.services.running.runtime_host import (
    RunnerHostManagedPaths,
    build_runner_cancel_controller,
    build_runner_host_bundle,
    build_runner_host_paths,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedRunnerExecution:
    request: CaseExecutionRequest
    attempt_index: int
    paths: RunPaths
    host_paths: RunnerHostManagedPaths
    execution: ExecutionOutcome
    events: list[RunEvent]
    artifacts: dict[str, str]
    runtime_output: RunnerRuntimeOutput | None = None
    failure_exc: Exception | None = None
    runtime_context_available: bool = False


class OperationTrackerLike(Protocol):
    operation_id: str

    def append_run_event(self, event: RunEvent) -> None: ...

    def get_record(self) -> Any: ...

    def should_cancel(self) -> bool: ...

    def append_event(
        self,
        *,
        event_type: str,
        message: str | None,
        data: dict[str, object] | None = None,
    ) -> None: ...

    def update_progress(self, **progress: Any) -> Any: ...


class RunService:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None = None,
        operation_tracker: OperationTracker | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._default_event_sink = event_sink
        self._default_operation_tracker = operation_tracker
        self._materializer = RunnerArtifactMaterializer(
            resolved_config=resolved_config,
            operation_tracker=operation_tracker,
        )
        self._orchestration_materializer = OrchestrationArtifactMaterializer(
            resolved_config=resolved_config,
            operation_tracker=operation_tracker,
        )

    def execute_case(self, request: CaseExecutionRequest) -> CaseExecutionResult:
        judge_runtime = resolve_judge_runtime(resolved_config=self._resolved_config)
        policy = resolve_orchestration_policy(self._resolved_config.config)
        orchestration_request = CaseOrchestrationRequest(
            app_id=request.app_id,
            plan_id=request.plan_id,
            case=request.case,
            app_target=request.app_target,
            device_ref=request.device_ref,
            artifact_path=request.artifact_path,
            assets_root=request.assets_root,
            runtime_overrides=dict(request.runtime_overrides),
            policy=policy,
        )
        engine = DeterministicOrchestrationEngine(
            run_service=self,
            resolved_config=self._resolved_config,
            tracker=self._default_operation_tracker,
            judge_runtime=judge_runtime,
        )
        orchestration_result = engine.execute_case(orchestration_request)
        materialized = self._orchestration_materializer.materialize(
            request=request,
            orchestration_result=orchestration_result,
            run_dir=Path(orchestration_result.artifacts.get("run_dir", "")) if orchestration_result.artifacts.get("run_dir") else orchestration_result.attempts[-1].runner.run_dir,
        )
        return materialized.result

    def execute_case_runtime_stage(
        self,
        request: CaseExecutionRequest,
        *,
        attempt_index: int = 0,
    ) -> PreparedRunnerExecution:
        session = RunExecutionSession(request=request)
        tracker = self._default_operation_tracker
        host_paths: RunnerHostManagedPaths | None = None
        if tracker is not None:
            session.cancel_checker = tracker.should_cancel
        runtime_output: RunnerRuntimeOutput | None = None
        failure_exc: Exception | None = None
        execution: ExecutionOutcome | None = None

        try:
            paths = prepare_run_paths()
            session.paths = paths
            host_paths = build_runner_host_paths(paths)
            session.status = RunStatus(running=True, run_dir=paths.run_dir)

            def event_sink(event: RunEvent) -> None:
                self._publish(session, event, attempt_index=attempt_index)


            setup_logging(paths.log_path, event_sink=cast(RunEventSink, event_sink))
            logger.info("boot_stage=runtime_start")
            self._publish(
                session,
                RunStartedEvent(
                    message="run started",
                    data=build_run_started_event_payload(
                        run_dir=str(paths.run_dir),
                        case_title=request.case.title,
                    ),
                ),
                attempt_index=attempt_index,
            )
            host_bundle = build_runner_host_bundle(
                request=request,
                resolved_config=self._resolved_config,
                paths=paths,
                tracker=tracker,
                event_sink=event_sink,
                attempt_index=attempt_index,
            )
            session.context = host_bundle.runtime_context
            runtime = create_runner_runtime(
                resolved_config=self._resolved_config,
                event_sink=event_sink,
            )
            llm_observer = (
                build_llm_timeline_observer(
                    tracker=tracker,
                    agent_role="runner",
                    attempt_index=attempt_index,
                    app_id=request.app_id,
                    plan_id=request.plan_id,
                    case_id=request.case.case_id,
                )
                if tracker is not None
                else None
            )
            with llm_transcript_observer_scope(llm_observer):
                runtime_output = runtime.run(
                    host_bundle.runner_request,
                    context=host_bundle.runtime_context,
                    cancel_controller=build_runner_cancel_controller(tracker=tracker),
                )
            session.status = RunStatus(
                running=False,
                run_dir=paths.run_dir,
                steps_completed=runtime_output.result_data.steps_completed,
                last_event_type=RunEventType.RUN_STOPPED.value,
                stop_requested=session.stop_requested,
            )
            execution = ExecutionOutcome(
                status=runtime_output.result_data.status,
                stop_reason=runtime_output.result_data.stop_reason,
                steps_completed=runtime_output.result_data.steps_completed,
                last_action_summary=runtime_output.result_data.last_action_summary,
                last_target_identity=runtime_output.result_data.last_target_identity,
                last_surface_identity=runtime_output.result_data.last_surface_identity,
            )
        except Exception as exc:
            failure_exc = exc
            run_dir = session.status.run_dir
            if run_dir is None:
                fallback_paths = prepare_run_paths()
                run_dir = fallback_paths.run_dir
                session.paths = fallback_paths
                host_paths = build_runner_host_paths(fallback_paths)
                self._write_case_request(session)
            session.status = RunStatus(
                running=False,
                run_dir=run_dir,
                last_event_type=RunEventType.RUN_FAILED.value,
                stop_requested=session.stop_requested,
            )
            self._publish(
                session,
                RunFailedEvent(
                    message=str(exc),
                    data=build_run_failed_event_payload(run_dir=str(run_dir)),
                ),
                attempt_index=attempt_index,
            )
            execution = ExecutionOutcome(
                status="failed",
                stop_reason="run_failed",
                steps_completed=0,
                error_message=str(exc),
                error_type=type(exc).__name__,
            )
        finally:
            self._close_runtime_device(session.context)

        if session.paths is None:
            fallback_paths = prepare_run_paths()
            session.paths = fallback_paths
            host_paths = build_runner_host_paths(fallback_paths)
            self._write_case_request(session)
        effective_host_paths = host_paths or build_runner_host_paths(session.paths)
        if execution is None:
            raise RuntimeError("runner execution finished without an execution outcome")
        return PreparedRunnerExecution(
            request=request,
            attempt_index=attempt_index,
            paths=session.paths,
            host_paths=effective_host_paths,
            execution=execution,
            events=list(session.events),
            artifacts=self._build_stage_artifacts(
                host_paths=effective_host_paths,
                request=request,
                paths=session.paths,
                run_dir=session.status.run_dir,
            ),
            runtime_output=runtime_output,
            failure_exc=failure_exc,
            runtime_context_available=session.context is not None,
        )

    def _publish(self, session: RunExecutionSession, event: RunEvent, *, attempt_index: int) -> None:
        event = with_run_event_context(
            event,
            app_id=session.request.app_id,
            plan_id=session.request.plan_id,
            case_id=session.request.case.case_id,
            attempt_index=attempt_index,
        )
        session.events.append(event)
        session.status = RunStatus(
            running=session.status.running,
            run_dir=session.status.run_dir,
            steps_completed=session.status.steps_completed,
            last_event_type=event.type.value,
            stop_requested=session.stop_requested,
        )
        external_sink = self._default_event_sink
        tracker = self._default_operation_tracker
        if tracker is not None:
            tracker.append_run_event(event)
        if external_sink is not None:
            cast(RunEventSink, external_sink)(event)

    @staticmethod
    def _close_runtime_device(context) -> None:  # noqa: ANN001
        if context is None:
            return
        operation_id = getattr(context, "operation_id", None)
        device = getattr(context, "device", None)
        try:
            if isinstance(device, SupportsClose):
                try:
                    device.close()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("runtime_device_close_failed error=%s", exc)
        finally:
            unbind_operation_device(operation_id=operation_id, device=device)

    def _write_case_request(self, session: RunExecutionSession) -> None:
        paths = session.paths
        if paths is None or paths.case_path is None:
            return
        with paths.case_path.open("w", encoding="utf-8") as f:
            f.write(session.request.model_dump_json(indent=2))

    @staticmethod
    def _build_stage_artifacts(
        *,
        host_paths: RunnerHostManagedPaths,
        request: CaseExecutionRequest,
        paths: RunPaths,
        run_dir: Path | None,
    ) -> dict[str, str]:
        effective_run_dir = run_dir or host_paths.root_dir
        artifacts: dict[str, str] = {
            ARTIFACT_ID_ARTIFACT_MANIFEST: str(host_paths.artifact_manifest_path),
            ARTIFACT_ID_DIAGNOSTICS: str(host_paths.diagnostics_path),
        }
        for artifact_id, path in paths.publishable_artifacts().items():
            artifacts[artifact_id] = str(path)
        ios_bridge_dir = effective_run_dir / "ios_bridge"
        if ios_bridge_dir.exists():
            artifacts["ios_bridge"] = str(ios_bridge_dir)
            for artifact_id, path in {
                "ios_bridge_session": ios_bridge_dir / "session.json",
                "ios_bridge_events": ios_bridge_dir / "events.jsonl",
                "ios_bridge_summary": ios_bridge_dir / "summary.json",
            }.items():
                if path.exists():
                    artifacts[artifact_id] = str(path)
        if request.artifact_path is not None:
            artifacts["input_artifact"] = str(request.artifact_path)
        return artifacts
