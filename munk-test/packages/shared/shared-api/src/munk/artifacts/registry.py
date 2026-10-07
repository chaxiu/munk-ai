from __future__ import annotations

from dataclasses import dataclass

ARTIFACT_ID_CASE = "case"
ARTIFACT_ID_RESULT = "result"
ARTIFACT_ID_LOG = "log"
ARTIFACT_ID_ARTIFACT_MANIFEST = "artifact_manifest"
ARTIFACT_ID_DIAGNOSTICS = "diagnostics"
ARTIFACT_ID_DECISION_TRACE = "decision_trace"
ARTIFACT_ID_RUNNER_HISTORY = "runner_history"
ARTIFACT_ID_RUNNER_MEMORY = "runner_memory"
ARTIFACT_ID_RUNNER_ISSUES = "runner_issues"
ARTIFACT_ID_CONTEXT_PREP = "context_prep"
ARTIFACT_ID_RUNTIME_LOGS = "runtime_logs"
ARTIFACT_ID_RAW_SCREENSHOTS = "raw_screenshots"
ARTIFACT_ID_ANNOTATED_SCREENSHOTS = "annotated_screenshots"
ARTIFACT_ID_OBSERVATION_FRAMES = "observation_frames"
ARTIFACT_ID_OBSERVATION_DIFFS = "observation_diffs"
ARTIFACT_ID_OBSERVATION_TREE = "observation_tree"
ARTIFACT_ID_LLM_TRANSCRIPT = "llm_transcript"


@dataclass(frozen=True)
class ArtifactSpec:
    artifact_id: str
    run_paths_attr: str
    label: str | None = None
    require_existing_path: bool = False


RUN_PATH_OPTIONAL_ARTIFACT_SPECS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(artifact_id=ARTIFACT_ID_DECISION_TRACE, run_paths_attr="decision_trace_path"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_RUNNER_HISTORY, run_paths_attr="runner_history_path"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_RUNNER_MEMORY, run_paths_attr="runner_memory_path"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_RUNNER_ISSUES, run_paths_attr="runner_issues_path"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_CONTEXT_PREP, run_paths_attr="context_prep_path"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_RUNTIME_LOGS, run_paths_attr="runtime_logs_dir"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_RAW_SCREENSHOTS, run_paths_attr="raw_dir"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_ANNOTATED_SCREENSHOTS, run_paths_attr="annotated_dir"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_OBSERVATION_FRAMES, run_paths_attr="observation_frames_dir"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_OBSERVATION_DIFFS, run_paths_attr="observation_diffs_dir"),
    ArtifactSpec(artifact_id=ARTIFACT_ID_OBSERVATION_TREE, run_paths_attr="observation_tree_dir"),
    ArtifactSpec(
        artifact_id=ARTIFACT_ID_LLM_TRANSCRIPT,
        run_paths_attr="llm_transcript_path",
        require_existing_path=True,
    ),
)

ARTIFACT_LABELS: dict[str, str] = {
    spec.artifact_id: spec.label or spec.artifact_id
    for spec in RUN_PATH_OPTIONAL_ARTIFACT_SPECS
}
ARTIFACT_LABELS.update(
    {
        ARTIFACT_ID_CASE: ARTIFACT_ID_CASE,
        ARTIFACT_ID_RESULT: ARTIFACT_ID_RESULT,
        ARTIFACT_ID_LOG: ARTIFACT_ID_LOG,
        ARTIFACT_ID_ARTIFACT_MANIFEST: ARTIFACT_ID_ARTIFACT_MANIFEST,
        ARTIFACT_ID_DIAGNOSTICS: ARTIFACT_ID_DIAGNOSTICS,
    }
)


def artifact_label(artifact_id: str) -> str:
    return ARTIFACT_LABELS.get(artifact_id, artifact_id)
