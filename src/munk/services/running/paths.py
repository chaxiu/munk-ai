from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from munk.agent_base.llm import prepare_llm_transcript_path
from munk.paths import runtime_root
from munk.services.models import RunPaths
from munk.user_data import runs_home

__all__ = ["runtime_root", "create_unique_run_dir", "prepare_run_paths"]


def create_unique_run_dir(*, prefix: str) -> Path:
    runs_dir = runs_home()
    runs_dir.mkdir(parents=True, exist_ok=True)
    for _attempt in range(8):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        suffix = uuid4().hex[:8]
        run_dir = runs_dir / f"{prefix}_{timestamp}_{suffix}"
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise RuntimeError(f"failed to allocate unique run directory for prefix '{prefix}'")


def prepare_run_paths() -> RunPaths:
    run_dir = create_unique_run_dir(prefix="run")
    raw_dir = run_dir / "screenshots" / "raw"
    annotated_dir = run_dir / "screenshots" / "annotated"
    runtime_logs_dir = run_dir / "runtime_logs"
    observation_dir = run_dir / "observation"
    observation_frames_dir = observation_dir / "frames"
    observation_diffs_dir = observation_dir / "diffs"
    observation_tree_dir = observation_dir / "tree"
    raw_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)
    runtime_logs_dir.mkdir(parents=True, exist_ok=True)
    observation_frames_dir.mkdir(parents=True, exist_ok=True)
    observation_diffs_dir.mkdir(parents=True, exist_ok=True)
    observation_tree_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "run.log"
    decision_trace_path = run_dir / "decision_trace.jsonl"
    decision_trace_path.touch()
    runner_history_path = run_dir / "runner_history.json"
    runner_history_path.write_text("[]\n", encoding="utf-8")
    runner_memory_path = run_dir / "runner_memory.json"
    runner_memory_path.write_text('{\n  "entries": []\n}\n', encoding="utf-8")
    llm_transcript_path = prepare_llm_transcript_path(run_dir)
    context_prep_path = run_dir / "runner_context_prep.json"
    return RunPaths(
        run_dir=run_dir,
        log_path=log_path,
        raw_dir=raw_dir,
        annotated_dir=annotated_dir,
        runtime_logs_dir=runtime_logs_dir,
        observation_dir=observation_dir,
        observation_frames_dir=observation_frames_dir,
        observation_diffs_dir=observation_diffs_dir,
        observation_tree_dir=observation_tree_dir,
        case_path=run_dir / "case.json",
        result_path=run_dir / "result.json",
        decision_trace_path=decision_trace_path,
        runner_history_path=runner_history_path,
        runner_memory_path=runner_memory_path,
        llm_transcript_path=llm_transcript_path,
        context_prep_path=context_prep_path,
    )
