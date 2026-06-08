from __future__ import annotations

import json

from munk.judging.models import JudgeEvidenceBundle, JudgeExecutionSummary, JudgeRequest
from munk_judge_local.evidence_builder import build_evidence_pack


def build_request(tmp_path) -> JudgeRequest:  # noqa: ANN001
    return JudgeRequest(
        app_id="app-1",
        plan_id="plan-1",
        case_id="case-1",
        case_title="Add Task",
        intent="Add a new task",
        expected=["New Task is visible in the task list"],
        runner_goal="Create New Task",
        execution=JudgeExecutionSummary(
            status="completed",
            steps_completed=3,
            last_target_identity="com.example.todo",
            last_surface_identity="com.example.todo/.TaskListActivity",
        ),
        evidence_bundle=JudgeEvidenceBundle(
            observation_frames_path=tmp_path / "frames",
            observation_diffs_path=tmp_path / "diffs",
            observation_tree_path=tmp_path / "tree",
            runner_history_path=tmp_path / "runner_history.json",
            raw_screenshots_path=tmp_path / "raw",
        ),
    )


def test_build_evidence_pack_selects_relevant_observation_as_primary(tmp_path) -> None:  # noqa: ANN001
    frames_dir = tmp_path / "frames"
    diffs_dir = tmp_path / "diffs"
    tree_dir = tmp_path / "tree"
    raw_dir = tmp_path / "raw"
    history_path = tmp_path / "runner_history.json"
    frames_dir.mkdir()
    diffs_dir.mkdir()
    tree_dir.mkdir()
    raw_dir.mkdir()
    (frames_dir / "step_0001.json").write_text(
        json.dumps(
            {
                "package": "com.example.todo",
                "tree_available": True,
                "tree_summary": "nodes=3",
                "tree_nodes": [
                    {
                        "node_id": "1",
                        "stable_key": "rid:com.example.todo:id/task_title",
                        "text": "New Task",
                        "content_desc": None,
                        "resource_id": "com.example.todo:id/task_title",
                        "class_name": "android.widget.TextView",
                        "bounds": [0, 0, 100, 40],
                        "clickable": False,
                        "checkable": False,
                        "enabled": True,
                        "focused": False,
                        "selected": False,
                        "scrollable": False,
                        "checked": False,
                        "matched_visual_ids": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (diffs_dir / "step_0001.json").write_text(
        json.dumps(
            {
                "summary": "screen_changed=yes; appeared_nodes=New Task",
                "appeared_nodes": [{"label": "New Task"}],
                "updated_nodes": [],
                "disappeared_nodes": [],
                "linked_visual_changes": ["appeared New Task"],
            }
        ),
        encoding="utf-8",
    )
    (tree_dir / "step_0001.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="New Task" resource-id="com.example.todo:id/task_title" class="android.widget.TextView" package="com.example.todo" content-desc="" bounds="[0,0][100,40]" />
</hierarchy>
""",
        encoding="utf-8",
    )
    (raw_dir / "step_0001.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    history_path.write_text(
        json.dumps(
            [
                {
                    "step_index": 2,
                    "action_type": "stop",
                    "summary": "stop after verifying task",
                    "outcome_summary": "New Task is visible in the task list",
                }
            ]
        ),
        encoding="utf-8",
    )

    pack = build_evidence_pack(request=build_request(tmp_path))

    primary_kinds = [item.kind for item in pack.primary_evidence]
    assert "screen_diff" in primary_kinds
    assert "runner_history" in primary_kinds
    assert "screen_frame" in primary_kinds
    frame_item = next(item for item in pack.primary_evidence if item.kind == "screen_frame")
    compact_tree = frame_item.payload["excerpt"]["compact_tree"]
    assert compact_tree["node_count"] == 1
    assert compact_tree["nodes"][0]["txt"] == "New Task"
    assert pack.recent_raw_screenshots[0].step_index == 1
    assert pack.recent_raw_screenshots[0].tree_evidence_id == "screen_frame-step_0001"
    assert pack.evidence[0].evidence_id == "execution"
