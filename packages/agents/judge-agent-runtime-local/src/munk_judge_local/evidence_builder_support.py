from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

from munk.judging.models import (
    JudgeDecisionTraceEvidence,
    JudgeDecisionTraceEvidencePayload,
    JudgeEventEvidence,
    JudgeEventEvidencePayload,
    JudgeEventRecord,
    JudgeEvidence,
    JudgeRunnerHistoryEvidence,
    JudgeRunnerHistoryEvidencePayload,
    JudgeRunnerIssueEvidence,
    JudgeRunnerIssueEvidencePayload,
    JudgeRunnerIssueRecord,
    JudgeRunnerMemoryEvidence,
    JudgeRunnerMemoryEvidencePayload,
    JudgeRuntimeErrorLogEvidence,
    JudgeRuntimeErrorLogEvidencePayload,
    JudgeScreenshotEvidence,
    JudgeScreenshotEvidencePayload,
    is_runner_history_evidence,
    is_runner_issue_evidence,
    is_runner_memory_evidence,
    is_screen_diff_evidence,
    is_screen_frame_evidence,
)

from .evidence_builder_parsers import (
    _dict_list,
    _dict_or_none,
    _json_object,
    _runner_history_entry,
    _runner_memory_entry,
    _runtime_log_entry,
    _string_list,
    _string_or_none,
)
from .models import JudgeScreenshotRef

SCREENSHOT_WINDOW = 3
RUNTIME_ERROR_LOG_CHAR_BUDGET = 4096


def _build_event_evidence(events: list[JudgeEventRecord]) -> list[JudgeEvidence]:
    evidence: list[JudgeEvidence] = []
    for index, event in enumerate(events):
        payload = event.data
        summary = event.message or event.event_type
        if payload:
            summary = f"{summary} | data={json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
        evidence.append(
            JudgeEventEvidence(
                evidence_id=f"event-{index}",
                kind="event",
                source="event",
                summary=summary,
                payload=JudgeEventEvidencePayload(
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    message=event.message,
                    data=payload,
                ),
            )
        )
    return evidence


def _build_trace_evidence(trace_path_value: str | None) -> list[JudgeEvidence]:
    if not trace_path_value:
        return []
    trace_path = Path(trace_path_value)
    if not trace_path.exists():
        return []
    lines = [line.strip() for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    evidence: list[JudgeEvidence] = []
    for index, line in enumerate(lines[-20:]):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"raw": line}
        payload_dict = cast(dict[str, object], payload) if isinstance(payload, dict) else {"raw": str(payload)}
        step = payload_dict.get("step")
        attempt = payload_dict.get("attempt")
        will_retry = payload_dict.get("will_retry")
        seeded_element_count = payload_dict.get("seeded_element_count")
        arguments = payload_dict.get("arguments")
        result_summary = str(payload_dict.get("result_summary", line))
        evidence.append(
            JudgeDecisionTraceEvidence(
                evidence_id=f"trace-{index}",
                kind="decision_trace",
                source="artifact",
                summary=str(result_summary),
                payload=JudgeDecisionTraceEvidencePayload(
                    path=str(trace_path),
                    step_index=step if isinstance(step, int) else None,
                    attempt_index=attempt if isinstance(attempt, int) else None,
                    decision=_string_or_none(payload_dict.get("decision")),
                    action=_string_or_none(payload_dict.get("action")),
                    summary=_string_or_none(payload_dict.get("summary")),
                    result_summary=str(result_summary),
                    tool_name=_string_or_none(payload_dict.get("tool_name")),
                    tool_names=_string_list(payload_dict.get("tool_names")),
                    arguments=_json_object(cast(dict[str, object], arguments)) if isinstance(arguments, dict) else {},
                    will_retry=will_retry if isinstance(will_retry, bool) else None,
                    seeded_element_count=seeded_element_count if isinstance(seeded_element_count, int) else None,
                    ui_elements_summary=_string_or_none(payload_dict.get("ui_elements")),
                    raw_line=line,
                ),
            )
        )
    return evidence


def _build_runner_history_evidence(history_path_value: str | None) -> list[JudgeEvidence]:
    if not history_path_value:
        return []
    history_path = Path(history_path_value)
    if not history_path.exists():
        return []
    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list) or not payload:
        return []
    entries = _dict_list(payload)
    if not entries:
        return []
    latest = entries[0]
    latest_action = str(latest.get("action_type", "unknown"))
    latest_outcome = str(latest.get("outcome_summary") or latest.get("summary") or "").strip()
    summary = f"runner_history artifact: latest={latest_action}"
    if latest_outcome:
        summary = f"{summary}; outcome={latest_outcome}"
    latest_step_index = max(
        (
            step_index
            for item in entries
            for step_index in [item.get("step_index")]
            if isinstance(step_index, int)
        ),
        default=-1,
    )
    return [
        JudgeRunnerHistoryEvidence(
            evidence_id="runner-history",
            kind="runner_history",
            source="artifact",
            summary=summary,
            payload=JudgeRunnerHistoryEvidencePayload(
                path=str(history_path),
                latest_step_index=latest_step_index,
                entries=[_runner_history_entry(item) for item in entries],
                excerpt=[_runner_history_entry(item) for item in entries[:8]],
            ),
        )
    ]


def _build_runner_memory_evidence(memory_path_value: str | None) -> list[JudgeEvidence]:
    if not memory_path_value:
        return []
    memory_path = Path(memory_path_value)
    if not memory_path.exists():
        return []
    try:
        payload = json.loads(memory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    payload_dict = _dict_or_none(payload)
    if payload_dict is None:
        return []
    entries = _dict_list(payload_dict.get("entries"))
    if not entries:
        return []
    keys = ", ".join(str(item.get("key")) for item in entries[:3] if item.get("key"))
    summary = f"runner memory artifact: keys={keys or 'none'}"
    excerpt = [
        {
            "key": item.get("key"),
            "summary": item.get("summary"),
            "updated_step_index": item.get("updated_step_index"),
        }
        for item in entries[:8]
    ]
    return [
        JudgeRunnerMemoryEvidence(
            evidence_id="runner-memory",
            kind="runner_memory",
            source="artifact",
            summary=summary,
            payload=JudgeRunnerMemoryEvidencePayload(
                path=str(memory_path),
                entries=[_runner_memory_entry(item) for item in entries],
                excerpt=[_runner_memory_entry(item) for item in excerpt],
            ),
        )
    ]


def _build_runner_issue_evidence(issue_path_value: str | None) -> list[JudgeEvidence]:
    if not issue_path_value:
        return []
    issue_path = Path(issue_path_value)
    if not issue_path.exists():
        return []
    try:
        payload = json.loads(issue_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    payload_dict = _dict_or_none(payload)
    if payload_dict is None:
        return []
    issues = _dict_list(payload_dict.get("issues"))
    if not issues:
        return []
    evidence: list[JudgeEvidence] = []
    for index, item in enumerate(issues):
        step_index = item.get("step_index")
        severity = _string_or_none(item.get("severity")) or "warning"
        summary = _string_or_none(item.get("summary")) or "none"
        evidence.append(
            JudgeRunnerIssueEvidence(
                evidence_id=f"runner-issue-{index}",
                kind="runner_issue",
                source="artifact",
                summary=f"step={step_index} severity={severity} summary={summary}",
                payload=JudgeRunnerIssueEvidencePayload(
                    path=str(issue_path),
                    issue=JudgeRunnerIssueRecord(
                        step_index=step_index if isinstance(step_index, int) else None,
                        severity=severity,
                        summary=summary,
                        record=_json_object(item),
                    ),
                ),
            )
        )
    return evidence


def _build_runtime_error_log_evidence(runtime_logs_path_value: str | None) -> list[JudgeEvidence]:
    if not runtime_logs_path_value:
        return []
    runtime_logs_dir = Path(runtime_logs_path_value)
    if not runtime_logs_dir.exists() or not runtime_logs_dir.is_dir():
        return []
    step_files = sorted(path for path in runtime_logs_dir.iterdir() if path.name.startswith("step_") and path.suffix == ".json")
    if not step_files:
        return []

    collected_entries: list[dict[str, object]] = []
    step_indexes: list[int] = []
    for path in step_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        payload_dict = _dict_or_none(payload)
        if payload_dict is None:
            continue
        entries = _dict_list(payload_dict.get("entries"))
        if not entries:
            continue
        error_entries = [
            item
            for item in entries
            if isinstance(item, dict) and str(item.get("level", "")).strip() == "error"
        ]
        if not error_entries:
            continue
        step_index = payload_dict.get("step_index")
        if isinstance(step_index, int):
            step_indexes.append(step_index)
        collected_entries.extend(error_entries)
    if not collected_entries:
        return []

    excerpt = _trim_runtime_error_log_excerpt(collected_entries)
    if not excerpt:
        return []
    summary = f"runtime error logs observed in {len(step_indexes) or 1} step(s)"
    if step_indexes:
        summary = f"{summary}; latest_step={max(step_indexes)}"
    return [
        JudgeRuntimeErrorLogEvidence(
            evidence_id="runtime-error-log",
            kind="runtime_error_log",
            source="artifact",
            summary=summary,
            payload=JudgeRuntimeErrorLogEvidencePayload(
                path=str(runtime_logs_dir),
                excerpt=excerpt,
                entries=[_runtime_log_entry(item) for item in collected_entries[-8:]],
                step_indexes=sorted(set(step_indexes)),
            ),
        )
    ]


def _build_screenshot_refs(
    *,
    kind: Literal["raw", "annotated"],
    directory_value: str | None,
    frame_evidence: list[JudgeEvidence],
    diff_evidence: list[JudgeEvidence],
    runner_history_evidence: list[JudgeEvidence],
) -> list[JudgeScreenshotRef]:
    if not directory_value:
        return []
    directory = Path(directory_value)
    if not directory.exists() or not directory.is_dir():
        return []
    files = sorted(path for path in directory.iterdir() if path.suffix.lower() == ".png")
    if not files:
        return []

    selected_files = files[-SCREENSHOT_WINDOW:]
    frame_meta_by_step: dict[int, tuple[str, str | None]] = {}
    for item in frame_evidence:
        if not is_screen_frame_evidence(item):
            continue
        frame_meta_by_step[item.payload.step_index] = (item.evidence_id, item.payload.package)
    diff_id_by_step = {
        item.payload.step_index: item.evidence_id
        for item in diff_evidence
        if is_screen_diff_evidence(item)
    }
    history_by_step = _runner_history_by_step(runner_history_evidence)

    refs: list[JudgeScreenshotRef] = []
    for path in selected_files:
        step_index = _step_index_from_name(path.stem)
        frame_meta = frame_meta_by_step.get(step_index, (None, None))
        history_entry = history_by_step.get(step_index - 1) or history_by_step.get(step_index)
        screenshot_kind: Literal["raw", "annotated"] = "raw" if kind == "raw" else "annotated"
        refs.append(
            JudgeScreenshotRef(
                screenshot_id=f"{kind}-{path.stem}",
                step_index=step_index,
                kind=screenshot_kind,
                path=str(path),
                package=frame_meta[1],
                action_summary=_string_or_none(history_entry.get("summary")) if history_entry else None,
                observation_summary=_string_or_none(history_entry.get("outcome_summary")) if history_entry else None,
                tree_evidence_id=frame_meta[0],
                diff_evidence_id=diff_id_by_step.get(step_index),
            )
        )
    return refs


def _build_screenshot_evidence(screenshots: list[JudgeScreenshotRef]) -> list[JudgeEvidence]:
    evidence: list[JudgeEvidence] = []
    for screenshot in screenshots:
        summary_parts = [f"{screenshot.kind} screenshot step={screenshot.step_index}"]
        if screenshot.action_summary:
            summary_parts.append(f"action={screenshot.action_summary}")
        if screenshot.observation_summary:
            summary_parts.append(f"observation={screenshot.observation_summary}")
        evidence.append(
            JudgeScreenshotEvidence(
                evidence_id=f"screenshot-{screenshot.screenshot_id}",
                kind="screenshot",
                source="artifact",
                summary="; ".join(summary_parts),
                payload=JudgeScreenshotEvidencePayload.model_validate(screenshot.model_dump(mode="json")),
            )
        )
    return evidence


def _runner_memory_summary(runner_memory_evidence: list[JudgeEvidence]) -> list[dict[str, object]]:
    for evidence in runner_memory_evidence:
        if is_runner_memory_evidence(evidence) and evidence.payload.excerpt:
            return [cast(dict[str, object], entry.model_dump(mode="json")) for entry in evidence.payload.excerpt]
    return []


def _runner_issue_summary(runner_issue_evidence: list[JudgeEvidence]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for evidence in runner_issue_evidence:
        if not is_runner_issue_evidence(evidence):
            continue
        items.append(cast(dict[str, object], evidence.payload.issue.model_dump(mode="json")))
    return items


def _runner_history_by_step(runner_history_evidence: list[JudgeEvidence]) -> dict[int, dict[str, object]]:
    for evidence in runner_history_evidence:
        if not is_runner_history_evidence(evidence) or not evidence.payload.entries:
            continue
        return {
            entry.step_index: cast(dict[str, object], entry.model_dump(mode="json"))
            for entry in evidence.payload.entries
            if isinstance(entry.step_index, int)
        }
    return {}


def _step_index_from_name(name: str) -> int:
    parts = name.rsplit("_", maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        return -1
    return int(parts[1])


def _trim_runtime_error_log_excerpt(entries: list[dict[str, object]]) -> str:
    lines: list[str] = []
    total = 0
    for entry in reversed(entries):
        message = str(entry.get("message", "")).strip()
        if not message:
            continue
        step_index = entry.get("step_index")
        source = str(entry.get("source", "")).strip() or "runtime"
        surface_identity = str(entry.get("surface_identity", "")).strip()
        prefix = f"step={step_index if isinstance(step_index, int) else 'unknown'} source={source}"
        if surface_identity:
            prefix = f"{prefix} surface={surface_identity}"
        line = f"- {prefix} message={message}"
        projected = total + len(line) + 1
        if lines and projected > RUNTIME_ERROR_LOG_CHAR_BUDGET:
            break
        if not lines and len(line) > RUNTIME_ERROR_LOG_CHAR_BUDGET:
            return line[:RUNTIME_ERROR_LOG_CHAR_BUDGET]
        lines.append(line)
        total = projected
    return "\n".join(reversed(lines))
