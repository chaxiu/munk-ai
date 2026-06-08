from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from munk.agent_base.output_strategy import resolve_output_strategy
from munk.agent_base.pydantic_model_factory import build_pydantic_ai_model
from munk.config.load import ResolvedConfig, load_config_context
from munk.config.resolve import resolve_role_model_config, resolve_runtime_config
from munk.recording import (
    RecordingAnalysisActionEvidence,
    RecordingAnalysisOutcomeEvidence,
    RecordingAnalysisResult,
    RecordingAnalysisScreenshotRef,
    RecordingAnalysisStep,
)
from munk.services.perception_runtime import build_perception_provider_for_runtime
from munk.testing import CaseStartState, TestCase

from .evidence_builder import enrich_recording_bundle_for_analysis
from .models import (
    MAX_STAGE_ATTEMPTS,
    AnalysisProgressCallback,
    AppendProcedureStepSubmission,
    FinalizeCaseSubmission,
    PreparedAnalysisContext,
    StepAttemptOutcome,
)
from .pydantic_analysis_agent import PydanticAiRecordingAnalysisAgent


class RecordingAnalysisService:
    def __init__(
        self,
        *,
        workspace_root: Path,
        resolved_config: ResolvedConfig | None = None,
        model: object | None = None,
        agent: PydanticAiRecordingAnalysisAgent | Any | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._resolved_config = resolved_config
        self._model = model
        self._agent = agent

    def analyze_bundle(
        self,
        bundle: dict[str, Any],
        progress_callback: AnalysisProgressCallback | None = None,
    ) -> RecordingAnalysisResult:
        try:
            prepared = self._prepare_analysis_context(bundle)
            if progress_callback is not None:
                progress_callback(
                    "bundle_loaded",
                    {
                        "recording_id": prepared.recording_id,
                        "total_steps": len(prepared.steps_payload),
                    },
                )
            analyzed_steps, warnings = self._run_step_stage(bundle, prepared, progress_callback=progress_callback)
            finalized = self._run_finalize_stage(
                bundle,
                analyzed_steps,
                warnings,
                progress_callback=progress_callback,
            )
            return self._materialize_and_persist(
                prepared=prepared,
                analyzed_steps=analyzed_steps,
                warnings=warnings,
                finalized=finalized,
            )
        except Exception as exc:
            return RecordingAnalysisResult(
                recording_id=cast(str, bundle["recording_id"]),
                status="failed",
                failure_reason=str(exc),
                source_summary=cast(str | None, bundle.get("source_summary")),
            )

    def _prepare_analysis_context(self, bundle: dict[str, Any]) -> PreparedAnalysisContext:
        steps_payload = cast(list[dict[str, Any]], bundle.get("steps") or [])
        recording_id = cast(str, bundle["recording_id"])
        if not steps_payload:
            raise RuntimeError("recording timeline is empty; unable to analyze test case")
        session = cast(dict[str, Any], bundle["session"])
        enriched_bundle = self._enrich_bundle(bundle)
        return PreparedAnalysisContext(
            recording_id=recording_id,
            session=session,
            source_summary=cast(str | None, enriched_bundle.get("source_summary")),
            steps_payload=cast(list[dict[str, Any]], enriched_bundle.get("steps") or []),
        )

    def _run_step_stage(
        self,
        bundle: dict[str, Any],
        prepared: PreparedAnalysisContext,
        *,
        progress_callback: AnalysisProgressCallback | None = None,
    ) -> tuple[list[RecordingAnalysisStep], list[str]]:
        agent = self._resolve_agent()
        analyzed_steps: list[RecordingAnalysisStep] = []
        history: list[str] = []
        warnings: list[str] = []
        total_steps = len(prepared.steps_payload)
        for step_payload in prepared.steps_payload:
            entry = cast(dict[str, Any], step_payload["entry"])
            if progress_callback is not None:
                progress_callback(
                    "step_started",
                    {
                        "recording_id": prepared.recording_id,
                        "current_step_seq": cast(int, entry["seq"]),
                        "completed_steps": len(analyzed_steps),
                        "total_steps": total_steps,
                    },
                )
            analyzed_step = self._run_step_with_retries(
                agent=agent,
                bundle=bundle,
                step_payload=step_payload,
                history=history,
                recording_id=prepared.recording_id,
            )
            history.append(analyzed_step.procedure_step or analyzed_step.summary or analyzed_step.kind)
            warnings.extend(analyzed_step.warnings)
            analyzed_steps.append(analyzed_step)
            if progress_callback is not None:
                progress_callback(
                    "step_completed",
                    {
                        "recording_id": prepared.recording_id,
                        "current_step_seq": analyzed_step.seq,
                        "completed_steps": len(analyzed_steps),
                        "total_steps": total_steps,
                    },
                )
        return analyzed_steps, warnings

    def _run_step_with_retries(
        self,
        *,
        agent: Any,
        bundle: dict[str, Any],
        step_payload: dict[str, Any],
        history: list[str],
        recording_id: str,
    ) -> RecordingAnalysisStep:
        last_error = "step agent finished without returning a structured step analysis"
        last_outcome: StepAttemptOutcome | None = None
        for attempt_index in range(1, MAX_STAGE_ATTEMPTS + 1):
            outcome = agent.run_step_attempt(
                bundle=bundle,
                step=step_payload,
                history_procedure=history,
                attempt_index=attempt_index,
                retry_feedback=last_error if attempt_index > 1 else None,
            )
            last_outcome = outcome
            if outcome.submission is not None:
                return self._build_analysis_step(recording_id, step_payload, outcome.submission)
            last_error = outcome.last_error or (
                "step agent finished without returning a structured step analysis; "
                f"last_output={outcome.output_excerpt}"
            )
            if "request_limit" in last_error or "tool budget exhausted" in last_error:
                raise RuntimeError(
                    f"step {cast(dict[str, Any], step_payload['entry']).get('seq')} analysis did not converge: {last_error}"
                )
        raise RuntimeError(last_error if last_outcome is None else last_error)

    def _build_analysis_step(
        self,
        recording_id: str,
        step_payload: dict[str, Any],
        submission: AppendProcedureStepSubmission,
    ) -> RecordingAnalysisStep:
        entry = cast(dict[str, Any], step_payload["entry"])
        before_ref = RecordingAnalysisScreenshotRef.model_validate(step_payload["before_screenshot"])
        after_ref = RecordingAnalysisScreenshotRef.model_validate(step_payload["after_screenshot"])
        action_evidence = (
            RecordingAnalysisActionEvidence.model_validate(step_payload["action_evidence"])
            if step_payload.get("action_evidence") is not None
            else None
        )
        outcome_evidence = (
            RecordingAnalysisOutcomeEvidence.model_validate(step_payload["outcome_evidence"])
            if step_payload.get("outcome_evidence") is not None
            else None
        )
        step_warnings: list[str] = [
            *list(action_evidence.warnings if action_evidence is not None else []),
            *list(outcome_evidence.warnings if outcome_evidence is not None else []),
            *list(submission.warnings),
        ]
        procedure_step = _compose_procedure_step(
            action=submission.action,
            intent=submission.intent,
            state_change=submission.state_change,
        )
        return RecordingAnalysisStep(
            recording_id=recording_id,
            entry_id=cast(str, entry["entry_id"]),
            seq=cast(int, entry["seq"]),
            kind=cast(Any, entry["kind"]),
            summary=cast(str | None, entry.get("summary")),
            action=submission.action,
            intent=submission.intent,
            state_change=submission.state_change,
            procedure_step=procedure_step,
            before_observation_id=before_ref.observation_id,
            after_observation_id=after_ref.observation_id,
            before_screenshot=before_ref,
            after_screenshot=after_ref,
            action_evidence=action_evidence,
            outcome_evidence=outcome_evidence,
            warnings=step_warnings,
        )

    def _run_finalize_stage(
        self,
        bundle: dict[str, Any],
        analyzed_steps: list[RecordingAnalysisStep],
        warnings: list[str],
        *,
        progress_callback: AnalysisProgressCallback | None = None,
    ) -> FinalizeCaseSubmission:
        agent = self._resolve_agent()
        last_error = "finalize agent finished without returning a structured case draft"
        if progress_callback is not None:
            progress_callback(
                "finalize_started",
                {
                    "recording_id": cast(str, cast(dict[str, Any], bundle["session"]).get("recording_id")),
                    "completed_steps": len(analyzed_steps),
                    "total_steps": len(analyzed_steps),
                },
            )
        for attempt_index in range(1, MAX_STAGE_ATTEMPTS + 1):
            outcome = agent.run_finalize_attempt(
                bundle=bundle,
                analyzed_steps=analyzed_steps,
                warnings=warnings,
                attempt_index=attempt_index,
                retry_feedback=last_error if attempt_index > 1 else None,
            )
            if outcome.submission is not None:
                return outcome.submission
            last_error = outcome.last_error or (
                "finalize agent finished without returning a structured case draft; "
                f"last_output={outcome.output_excerpt}"
            )
            if "request_limit" in last_error or "tool budget exhausted" in last_error:
                raise RuntimeError(f"recording analysis finalization did not converge: {last_error}")
        raise RuntimeError(last_error)

    def _materialize_and_persist(
        self,
        *,
        prepared: PreparedAnalysisContext,
        analyzed_steps: list[RecordingAnalysisStep],
        warnings: list[str],
        finalized: FinalizeCaseSubmission,
    ) -> RecordingAnalysisResult:
        test_case = TestCase(
            case_id=cast(str, prepared.session.get("case_id") or f"{prepared.recording_id}-recorded"),
            title=finalized.title,
            intent=finalized.intent,
            expected=finalized.expected,
            procedure=[item.procedure_step or item.summary or item.kind for item in analyzed_steps],
            runner_goal=finalized.runner_goal,
            start_state=CaseStartState(page_id=None),
        )
        return RecordingAnalysisResult(
            recording_id=prepared.recording_id,
            status="completed",
            test_case=test_case,
            steps=analyzed_steps,
            source_summary=prepared.source_summary,
            warnings=warnings,
            export_ready=True,
        )

    def _resolve_agent(self) -> Any:
        if self._agent is not None:
            return self._agent
        resolved_config = self._resolved_config or load_config_context(None, workspace_root=self._workspace_root)
        if resolved_config is None:
            raise RuntimeError("recording analysis requires a configured LLM, but no config file was found")
        resolved_model = self._resolve_model_config(resolved_config)
        model = self._model or build_pydantic_ai_model(resolved_model, config=resolved_config.config)
        runtime_config = resolve_runtime_config(resolved_config.config)
        self._agent = PydanticAiRecordingAnalysisAgent(
            model=model,
            output_strategy=resolve_output_strategy(resolved_model),
            max_tokens=runtime_config.max_tokens,
            temperature=runtime_config.temperature,
            vl_max_side=runtime_config.vl_max_side,
        )
        return self._agent

    def _resolve_model_config(self, resolved_config: ResolvedConfig | None = None) -> Any:
        resolved_config = resolved_config or self._resolved_config or load_config_context(None, workspace_root=self._workspace_root)
        if resolved_config is None:
            raise RuntimeError("recording analysis requires a configured LLM, but no config file was found")
        resolved = (
            resolve_role_model_config(resolved_config.config, role="analysis")
            or resolve_role_model_config(resolved_config.config, role="review")
            or resolve_role_model_config(resolved_config.config, role="judge")
            or resolve_role_model_config(resolved_config.config, role="runner")
        )
        if resolved is None:
            raise RuntimeError("recording analysis could not resolve a model configuration")
        return resolved

    def _enrich_bundle(self, bundle: dict[str, Any]) -> dict[str, Any]:
        if self._agent is not None:
            return bundle
        resolved_config = self._resolved_config or load_config_context(None, workspace_root=self._workspace_root)
        if resolved_config is None:
            return bundle
        runtime_config = resolve_runtime_config(resolved_config.config)
        provider = build_perception_provider_for_runtime(
            resolved_config.config,
            max_side=runtime_config.max_side,
            icon_conf=runtime_config.icon_conf,
        )
        return enrich_recording_bundle_for_analysis(
            bundle,
            perception=provider,
            icon_conf=runtime_config.icon_conf,
        )


def _compose_procedure_step(*, action: str, intent: str, state_change: str) -> str:
    return f"{intent}，{action}，{state_change}"
