from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import cast

from munk.judging.models import JudgeEvidence

from munk.runtime_defaults import DEFAULT_VL_MAX_SIDE

from .models import JudgeEvidencePack, JudgeScreenshotRef

_STEP_INDEX_PATTERN = re.compile(r"step[_-]?0*(\d+)")


@dataclass
class JudgeRunDeps:
    evidence_pack: JudgeEvidencePack
    vl_max_side: int = DEFAULT_VL_MAX_SIDE
    tool_budget: int = 2
    tool_calls: list[str] = field(default_factory=list)

    def evidence_by_id(self) -> dict[str, JudgeEvidence]:
        return {item.evidence_id: item for item in self.evidence_pack.evidence}

    def screen_evidence_by_step(self) -> dict[int, JudgeEvidence]:
        return self._evidence_by_step("screen_frame")

    def transition_evidence_by_step(self) -> dict[int, JudgeEvidence]:
        return self._evidence_by_step("screen_diff")

    def runner_history_by_step(self) -> dict[int, dict[str, object]]:
        for item in self.evidence_pack.evidence:
            if item.kind != "runner_history":
                continue
            entries = item.payload.get("entries")
            if not isinstance(entries, list):
                continue
            entries_list = cast(list[object], entries)
            indexed: dict[int, dict[str, object]] = {}
            for entry in entries_list:
                if not isinstance(entry, dict):
                    continue
                entry_dict = cast(dict[str, object], entry)
                step_index = entry_dict.get("step_index")
                if not isinstance(step_index, int):
                    continue
                indexed[step_index] = dict(entry_dict)
            return indexed
        return {}

    def runner_memory_entries(self) -> list[dict[str, object]]:
        for item in self.evidence_pack.evidence:
            if item.kind != "runner_memory":
                continue
            entries = item.payload.get("entries")
            if isinstance(entries, list):
                return [cast(dict[str, object], entry) for entry in entries if isinstance(entry, dict)]
        return []

    def runner_memory_by_key(self) -> dict[str, dict[str, object]]:
        indexed: dict[str, dict[str, object]] = {}
        for entry in self.runner_memory_entries():
            key = entry.get("key")
            if isinstance(key, str) and key.strip():
                indexed[key] = entry
        return indexed

    def recent_screenshot_refs_by_step(self) -> dict[int, JudgeScreenshotRef]:
        refs: dict[int, JudgeScreenshotRef] = {}
        for item in self.evidence_pack.recent_raw_screenshots:
            refs[item.step_index] = item
        for item in self.evidence_pack.recent_annotated_screenshots:
            refs.setdefault(item.step_index, item)
        return refs

    def raw_screenshot_refs_by_step(self) -> dict[int, JudgeScreenshotRef]:
        return {
            item.step_index: item
            for item in self.evidence_pack.recent_raw_screenshots
        }

    def _evidence_by_step(self, expected_kind: str) -> dict[int, JudgeEvidence]:
        indexed: dict[int, JudgeEvidence] = {}
        for item in self.evidence_pack.evidence:
            if item.kind != expected_kind:
                continue
            step_index = _extract_step_index(item)
            if step_index is not None:
                indexed[step_index] = item
        return indexed


def _extract_step_index(item: JudgeEvidence) -> int | None:
    raw_step_index = item.payload.get("step_index")
    if isinstance(raw_step_index, int):
        return raw_step_index
    match = _STEP_INDEX_PATTERN.search(item.evidence_id)
    if match is None:
        return None
    return int(match.group(1))
