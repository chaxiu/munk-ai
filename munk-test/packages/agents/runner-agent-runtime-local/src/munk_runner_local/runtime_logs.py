from __future__ import annotations

import json
import logging
from dataclasses import asdict, replace
from pathlib import Path

from munk.device import RuntimeLogEntry, SupportsRuntimeLogs

logger = logging.getLogger(__name__)


class RunLogCollector:
    def __init__(self, runtime: SupportsRuntimeLogs, *, logs_dir: Path) -> None:
        self._runtime = runtime
        self._logs_dir = logs_dir
        self._started = False
        self._raw_path = logs_dir / "raw.jsonl"

    def start(self) -> None:
        if self._started:
            return
        self._runtime.start_log_session()
        self._runtime.drain_runtime_logs()
        self._started = True

    def begin_step(self, step_index: int) -> None:
        del step_index
        if not self._started:
            return
        try:
            self._runtime.drain_runtime_logs()
        except Exception as exc:  # noqa: BLE001
            self._disable(exc, "begin_step")

    def finish_step(
        self,
        step_index: int,
        *,
        target_identity: str | None,
        surface_identity: str | None,
    ) -> None:
        if not self._started:
            return
        try:
            entries = [
                replace(
                    entry,
                    step_index=step_index,
                    target_identity=target_identity,
                    surface_identity=surface_identity,
                )
                for entry in self._runtime.drain_runtime_logs()
            ]
        except Exception as exc:  # noqa: BLE001
            self._disable(exc, "finish_step")
            return
        if not entries:
            return
        self._append_raw(entries)
        payload: dict[str, object] = {
            "step_index": step_index,
            "entry_count": len(entries),
            "error_count": sum(1 for entry in entries if entry.level == "error"),
            "warning_count": sum(1 for entry in entries if entry.level == "warning"),
            "entries": [asdict(entry) for entry in entries],
        }
        step_path = self._logs_dir / f"step_{step_index:04d}.json"
        step_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def finalize(self) -> None:
        if not self._started:
            return
        try:
            entries = self._runtime.drain_runtime_logs()
            if entries:
                self._append_raw(entries)
            self._runtime.stop_log_session()
        except Exception as exc:  # noqa: BLE001
            self._disable(exc, "finalize")
            return
        self._started = False

    def _append_raw(self, entries: list[RuntimeLogEntry]) -> None:
        with self._raw_path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(asdict(entry), ensure_ascii=False))
                handle.write("\n")

    def _disable(self, exc: Exception, phase: str) -> None:
        logger.warning("runtime_log_collection_disabled phase=%s error=%s", phase, exc)
        self._started = False
