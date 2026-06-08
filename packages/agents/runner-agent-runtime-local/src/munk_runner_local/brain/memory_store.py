from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import TypeAlias

from munk.services.events import utc_now_iso

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def _normalize_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("memory value keys must be strings")
            normalized[key] = _normalize_json_value(item)
        return normalized
    raise ValueError("memory value must be JSON-serializable")


@dataclass(frozen=True)
class RunnerMemoryEntry:
    key: str
    value: JsonValue
    summary: str
    updated_step_index: int | None
    timestamp: str


@dataclass
class RunnerMemoryStore:
    entries_by_key: dict[str, RunnerMemoryEntry] = field(default_factory=dict)

    def save(
        self,
        *,
        key: str,
        value: object,
        summary: str,
        step_index: int | None,
    ) -> tuple[RunnerMemoryEntry, bool]:
        cleaned_key = key.strip()
        cleaned_summary = summary.strip()
        if not cleaned_key:
            raise ValueError("memory key must not be empty")
        if not cleaned_summary:
            raise ValueError("memory summary must not be empty")
        normalized_value = _normalize_json_value(value)
        created = cleaned_key not in self.entries_by_key
        entry = RunnerMemoryEntry(
            key=cleaned_key,
            value=normalized_value,
            summary=cleaned_summary,
            updated_step_index=step_index,
            timestamp=utc_now_iso(),
        )
        self.entries_by_key[cleaned_key] = entry
        return entry, created

    def read_all(self) -> list[RunnerMemoryEntry]:
        return list(self.entries_by_key.values())

    def read_one(self, key: str) -> RunnerMemoryEntry | None:
        return self.entries_by_key.get(key.strip())

    def summary_items(self, *, limit: int | None = None) -> list[dict[str, object]]:
        items = [
            {
                "key": entry.key,
                "summary": entry.summary,
                "updated_step_index": entry.updated_step_index,
            }
            for entry in self.read_all()
        ]
        if limit is None:
            return items
        return items[: max(limit, 0)]

    def artifact_payload(self) -> dict[str, object]:
        return {
            "entries": [asdict(entry) for entry in self.read_all()],
        }

    def artifact_json(self) -> str:
        return json.dumps(self.artifact_payload(), ensure_ascii=False, indent=2) + "\n"
