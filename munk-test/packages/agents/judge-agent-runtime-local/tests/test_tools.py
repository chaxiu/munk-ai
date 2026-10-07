from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Callable, cast

from munk.judging.models import (
    JudgeCompactUiNode,
    JudgeCompactUiTree,
    JudgeExecutionSummary,
    JudgeFocusHit,
    JudgeRunnerHistoryEntry,
    JudgeRunnerHistoryEvidence,
    JudgeRunnerHistoryEvidencePayload,
    JudgeRunnerMemoryEntry,
    JudgeRunnerMemoryEvidence,
    JudgeRunnerMemoryEvidencePayload,
    JudgeScreenNodeChange,
    JudgeScreenDiffEvidence,
    JudgeScreenDiffEvidencePayload,
    JudgeScreenFrameEvidence,
    JudgeScreenFrameEvidencePayload,
)
from munk_judge_local.models import JudgeEvidencePack, JudgeScreenshotRef
from munk_judge_local.tool_models import JudgeRunDeps
from munk_judge_local.tools import _consume_budget, register_judge_tools


class CapturingAgent:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., object]] = {}

    def tool(self, func: Callable[..., object]) -> Callable[..., object]:
        self.tools[func.__name__] = func
        return func


def build_deps() -> JudgeRunDeps:
    pack = JudgeEvidencePack(
        plan_id="plan-1",
        case_id="case-1",
        case_title="Case One",
        intent="Add a task",
        expected=["New Task is visible"],
        runner_goal="Create task",
        execution=JudgeExecutionSummary(status="completed", steps_completed=3),
        primary_evidence=[
            JudgeScreenDiffEvidence(
                evidence_id="screen_diff-step_0002",
                kind="screen_diff",
                source="artifact",
                summary="screen_diff artifact: screen_changed=yes; appeared_nodes=New Task",
                payload=JudgeScreenDiffEvidencePayload(
                    path="/tmp/screen_diff-step_0002.json",
                    step_index=2,
                    summary="screen_changed=yes; appeared_nodes=New Task",
                    appeared_labels=["New Task"],
                    appeared_nodes=[JudgeScreenNodeChange(label="New Task")] * 6,
                    linked_visual_changes=["appeared New Task"] * 6,
                ),
            ),
            JudgeScreenFrameEvidence(
                evidence_id="screen_frame-step_0002",
                kind="screen_frame",
                source="artifact",
                summary="screen_frame artifact: focus_hits=New Task",
                payload=JudgeScreenFrameEvidencePayload(
                    path="/tmp/screen_frame-step_0002.json",
                    step_index=2,
                    package="com.example.todo",
                    compact_tree=JudgeCompactUiTree(
                        node_count=2,
                        nodes=[
                            JudgeCompactUiNode(text="New Task 0", resource_id="id/task_0", state={"checked": True}),
                            JudgeCompactUiNode(text="New Task 1", resource_id="id/task_1"),
                        ],
                    ),
                    focus_hits=[JudgeFocusHit(label="New Task 0", node_id="node-1", score=3)],
                ),
            ),
            JudgeRunnerHistoryEvidence(
                evidence_id="runner-history",
                kind="runner_history",
                source="artifact",
                summary="runner_history artifact: latest=click; outcome=New Task is visible",
                payload=JudgeRunnerHistoryEvidencePayload(
                    entries=[
                        JudgeRunnerHistoryEntry(
                            step_index=index,
                            action_type="click",
                            summary=f"action {index}",
                            outcome_summary=f"outcome {index}",
                        )
                        for index in range(1, 4)
                    ]
                ),
            ),
        ],
        recent_raw_screenshots=[
            JudgeScreenshotRef(
                screenshot_id="raw-step-0003",
                step_index=3,
                kind="raw",
                path="/tmp/step_0003.png",
                action_summary="action 3",
                observation_summary="outcome 3",
            )
        ],
        runner_memory_summary=[
            {
                "key": "baseline_users",
                "summary": "remember users before refresh",
                "updated_step_index": 0,
            }
        ],
        evidence=[
            JudgeScreenDiffEvidence(
                evidence_id="screen_diff-step_0002",
                kind="screen_diff",
                source="artifact",
                summary="screen_diff artifact: screen_changed=yes; appeared_nodes=New Task",
                payload=JudgeScreenDiffEvidencePayload(
                    path="/tmp/screen_diff-step_0002.json",
                    step_index=2,
                    summary="screen_changed=yes; appeared_nodes=New Task",
                    appeared_labels=["New Task"],
                    appeared_nodes=[JudgeScreenNodeChange(label="New Task")] * 6,
                    linked_visual_changes=["appeared New Task"] * 6,
                ),
            ),
            JudgeScreenFrameEvidence(
                evidence_id="screen_frame-step_0002",
                kind="screen_frame",
                source="artifact",
                summary="screen_frame artifact: focus_hits=New Task",
                payload=JudgeScreenFrameEvidencePayload(
                    path="/tmp/screen_frame-step_0002.json",
                    step_index=2,
                    package="com.example.todo",
                    compact_tree=JudgeCompactUiTree(
                        node_count=2,
                        nodes=[
                            JudgeCompactUiNode(text="New Task 0", resource_id="id/task_0", state={"checked": True}),
                            JudgeCompactUiNode(text="New Task 1", resource_id="id/task_1"),
                        ],
                    ),
                    focus_hits=[JudgeFocusHit(label="New Task 0", node_id="node-1", score=3)],
                ),
            ),
            JudgeScreenDiffEvidence(
                evidence_id="screen_diff-step_0003",
                kind="screen_diff",
                source="artifact",
                summary="screen_diff artifact: screen_changed=no",
                payload=JudgeScreenDiffEvidencePayload(
                    path="/tmp/screen_diff-step_0003.json",
                    step_index=3,
                    summary="screen_changed=no",
                ),
            ),
            JudgeRunnerHistoryEvidence(
                evidence_id="runner-history",
                kind="runner_history",
                source="artifact",
                summary="runner_history artifact: latest=click; outcome=New Task is visible",
                payload=JudgeRunnerHistoryEvidencePayload(
                    entries=[
                        JudgeRunnerHistoryEntry(
                            step_index=index,
                            action_type="click",
                            summary=f"action {index}",
                            outcome_summary=f"outcome {index}",
                        )
                        for index in range(1, 4)
                    ]
                ),
            ),
            JudgeRunnerMemoryEvidence(
                evidence_id="runner-memory",
                kind="runner_memory",
                source="artifact",
                summary="runner memory artifact: keys=baseline_users",
                payload=JudgeRunnerMemoryEvidencePayload(
                    entries=[
                        JudgeRunnerMemoryEntry(
                            key="baseline_users",
                            summary="remember users before refresh",
                            value=["alice", "bob"],
                            updated_step_index=0,
                            timestamp="2026-05-22T00:00:00+00:00",
                        )
                    ],
                    excerpt=[
                        JudgeRunnerMemoryEntry(
                            key="baseline_users",
                            summary="remember users before refresh",
                            updated_step_index=0,
                        )
                    ],
                ),
            ),
        ],
    )
    return JudgeRunDeps(evidence_pack=pack, vl_max_side=12, tool_budget=2)


def build_tools() -> dict[str, Callable[..., object]]:
    agent = CapturingAgent()
    register_judge_tools(cast(Any, agent))
    return agent.tools


def test_read_recent_step_summaries_returns_compact_recent_view() -> None:
    deps = build_deps()
    tools = build_tools()

    tool = cast(Callable[..., str], tools["read_recent_step_summaries"])
    payload = json.loads(tool(SimpleNamespace(deps=deps), last_n=2))

    assert [item["step_index"] for item in payload] == [2, 3]
    assert payload[0]["screen_change_status"] == "changed"
    assert payload[1]["screen_change_status"] == "unchanged"
    assert "compact_tree" not in payload[0]
    assert "changes" not in payload[0]


def test_consume_budget_stops_after_limit() -> None:
    deps = build_deps()

    assert _consume_budget(deps, "screen_diff") is True
    assert _consume_budget(deps, "screen_frame") is True
    assert _consume_budget(deps, "trace") is False
