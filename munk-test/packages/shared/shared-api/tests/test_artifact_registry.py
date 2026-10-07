from __future__ import annotations

from munk.artifacts import (
    ARTIFACT_ID_CASE,
    ARTIFACT_ID_LLM_TRANSCRIPT,
    ARTIFACT_ID_RESULT,
    RUN_PATH_OPTIONAL_ARTIFACT_SPECS,
    artifact_label,
)


def test_artifact_registry_exports_stable_ids() -> None:
    assert ARTIFACT_ID_CASE == "case"
    assert ARTIFACT_ID_RESULT == "result"
    assert ARTIFACT_ID_LLM_TRANSCRIPT == "llm_transcript"


def test_run_path_optional_artifact_specs_include_runner_outputs() -> None:
    artifact_ids = {spec.artifact_id for spec in RUN_PATH_OPTIONAL_ARTIFACT_SPECS}

    assert "runner_history" in artifact_ids
    assert "runner_memory" in artifact_ids
    assert "raw_screenshots" in artifact_ids


def test_artifact_label_is_stable_for_known_and_unknown_ids() -> None:
    assert artifact_label("runner_memory") == "runner_memory"
    assert artifact_label("unknown_artifact") == "unknown_artifact"
