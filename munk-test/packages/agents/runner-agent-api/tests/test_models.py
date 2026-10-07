from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from munk.app import AndroidAppIdentity, AppTarget
from munk.running.models import (
    RunnerManagedPaths,
    RunnerRequest,
    RunnerRuntimeContext,
    RunnerRuntimeOutput,
    RunnerRuntimeResultData,
)
from munk.running.runtime_overrides import apply_runtime_overrides, validate_runtime_override
from munk.services.models import RunPaths
from munk.testing import TestCase


def build_case() -> TestCase:
    return TestCase(
        case_id="case-1",
        title="Case One",
        intent="Open settings",
        expected=["Settings page is visible"],
        runner_goal="Open settings page",
    )


def build_target() -> AppTarget:
    return AppTarget(
        app_id="app-1",
        platform="android",
        android=AndroidAppIdentity(package_name="com.test.app"),
    )


def test_runner_request_accepts_minimal_valid_payload() -> None:
    request = RunnerRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case=build_case(),
        app_target=build_target(),
        runtime_overrides={"max_steps": 5},
    )
    assert request.case_id == "case-1"
    assert request.runtime_overrides["max_steps"] == 5


def test_runner_request_rejects_case_id_mismatch() -> None:
    with pytest.raises(ValueError, match="case_id must match case.case_id"):
        RunnerRequest(
            app_id="app-1",
            plan_id="plan-1",
            case_id="case-2",
            case=build_case(),
            app_target=build_target(),
        )


def test_runner_runtime_output_defaults_warning_summary() -> None:
    output = RunnerRuntimeOutput(
        result_data=RunnerRuntimeResultData(
            status="completed",
            steps_completed=3,
            last_action_summary="tap settings",
        ),
        started_at="2026-01-01T00:00:00Z",
        duration_ms=1200,
    )
    assert output.warning_summary == []
    assert output.result_data.steps_completed == 3


def test_runner_runtime_context_accepts_managed_paths_and_runtime_objects() -> None:
    context = RunnerRuntimeContext(
        operation_id="op-1",
        attempt_index=2,
        managed_paths=RunnerManagedPaths(
            root_dir=Path("/tmp/run"),
            request_dump_path=Path("/tmp/run/runner_request.json"),
            raw_dir=Path("/tmp/run/raw"),
            annotated_dir=Path("/tmp/run/annotated"),
            runtime_logs_dir=Path("/tmp/run/runtime_logs"),
            observation_frames_dir=Path("/tmp/run/observation/frames"),
            observation_diffs_dir=Path("/tmp/run/observation/diffs"),
            observation_tree_dir=Path("/tmp/run/observation/tree"),
            decision_trace_path=Path("/tmp/run/decision_trace.jsonl"),
            runner_history_path=Path("/tmp/run/runner_history.json"),
            runner_memory_path=Path("/tmp/run/runner_memory.json"),
            llm_transcript_path=Path("/tmp/run/llm_transcript.jsonl"),
            context_prep_path=Path("/tmp/run/context_prep.json"),
        ),
        device=SimpleNamespace(name="device"),
        perception=SimpleNamespace(name="perception"),
        progress=None,
    )
    assert context.operation_id == "op-1"
    assert context.attempt_index == 2
    assert context.managed_paths.request_dump_path.name == "runner_request.json"


def test_runner_managed_paths_round_trip_with_run_paths() -> None:
    paths = RunPaths(
        run_dir=Path("/tmp/run"),
        log_path=Path("/tmp/run/run.log"),
        raw_dir=Path("/tmp/run/raw"),
        annotated_dir=Path("/tmp/run/annotated"),
        runtime_logs_dir=Path("/tmp/run/runtime_logs"),
        observation_frames_dir=Path("/tmp/run/observation/frames"),
        observation_diffs_dir=Path("/tmp/run/observation/diffs"),
        observation_tree_dir=Path("/tmp/run/observation/tree"),
        case_path=Path("/tmp/run/case.json"),
        result_path=Path("/tmp/run/result.json"),
        decision_trace_path=Path("/tmp/run/decision_trace.jsonl"),
        runner_history_path=Path("/tmp/run/runner_history.json"),
        runner_memory_path=Path("/tmp/run/runner_memory.json"),
        runner_issues_path=Path("/tmp/run/runner_issues.json"),
        llm_transcript_path=Path("/tmp/run/llm_transcript.jsonl"),
        context_prep_path=Path("/tmp/run/context_prep.json"),
    )

    managed_paths = RunnerManagedPaths.from_run_paths(paths)
    rebuilt_paths = managed_paths.to_run_paths()

    assert managed_paths.request_dump_path == Path("/tmp/run/case.json")
    assert rebuilt_paths == paths


@dataclass(frozen=True)
class FakeRuntimeParams:
    max_steps: int = 30
    initial_ready_timeout_sec: float = 6.0
    runner_max_elements: int = 80
    settle_mode: str = "ratio"


def test_apply_runtime_overrides_updates_runtime_params_from_shared_registry() -> None:
    updated = apply_runtime_overrides(
        FakeRuntimeParams(),
        {
            "max_steps": 12,
            "initial_ready_timeout_sec": 1.5,
            "runner_max_elements": 24,
            "settle_mode": "delay",
        },
    )

    assert updated == FakeRuntimeParams(
        max_steps=12,
        initial_ready_timeout_sec=1.5,
        runner_max_elements=24,
        settle_mode="delay",
    )


def test_validate_runtime_override_rejects_managed_and_invalid_values() -> None:
    with pytest.raises(ValueError, match="managed by case context"):
        validate_runtime_override("device_ref", "device-1")
    with pytest.raises(ValueError, match="must be one of: strict, ratio, delay"):
        validate_runtime_override("settle_mode", "fast")
