from __future__ import annotations

import re
from datetime import datetime
from typing import cast

from munk.device import RuntimeLogEntry, RuntimeLogLevel

_LOGCAT_THREADTIME_PATTERN = re.compile(
    r"^(?P<month>\d{2})-(?P<day>\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"(?P<pid>\d+)\s+"
    r"(?P<tid>\d+)\s+"
    r"(?P<priority>[VDIWEAF])\s+"
    r"(?P<tag>.*?):\s(?P<message>.*)$"
)

_LOG_LEVELS = {
    "V": "debug",
    "D": "debug",
    "I": "info",
    "W": "warning",
    "E": "error",
    "A": "error",
    "F": "error",
}


def build_process_name_candidates(package_name: str | None) -> tuple[str, ...]:
    if not package_name:
        return ()
    return (package_name,)


def parse_logcat_entries(output: str) -> list[RuntimeLogEntry]:
    entries: list[RuntimeLogEntry] = []
    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        match = _LOGCAT_THREADTIME_PATTERN.match(line)
        if match is None:
            entries.append(
                RuntimeLogEntry(
                    timestamp_ms=None,
                    level="unknown",
                    source="android_logcat",
                    message=line,
                    raw={"line": line},
                )
            )
            continue
        raw = match.groupdict()
        message = raw["message"].strip()
        if not message:
            continue
        pid = int(raw["pid"])
        timestamp_ms = _parse_log_timestamp_ms(raw["month"], raw["day"], raw["time"])
        entries.append(
            RuntimeLogEntry(
                timestamp_ms=timestamp_ms,
                level=cast(RuntimeLogLevel, _LOG_LEVELS.get(raw["priority"], "unknown")),
                source="android_logcat",
                message=message,
                raw={
                    "line": line,
                    "pid": pid,
                    "tid": int(raw["tid"]),
                    "priority": raw["priority"],
                    "tag": raw["tag"].strip(),
                },
            )
        )
    return entries


def entry_pid(entry: RuntimeLogEntry) -> int | None:
    value = entry.raw.get("pid")
    if isinstance(value, int):
        return value
    return None


def matches_process_name(entry: RuntimeLogEntry, candidates: tuple[str, ...]) -> bool:
    line = str(entry.raw.get("line", "")).strip()
    tag = str(entry.raw.get("tag", "")).strip()
    message = entry.message
    searchable = "\n".join((line, tag, message))
    return any(candidate in searchable for candidate in candidates)


def entry_dedupe_key(entry: RuntimeLogEntry) -> tuple[object, ...]:
    return (
        entry.timestamp_ms,
        entry.level,
        entry.message,
        entry.raw.get("pid"),
        entry.raw.get("tag"),
    )


def _parse_log_timestamp_ms(month: str, day: str, time_value: str) -> int | None:
    try:
        current_year = datetime.now().year
        parsed = datetime.strptime(
            f"{current_year}-{month}-{day} {time_value}",
            "%Y-%m-%d %H:%M:%S.%f",
        )
    except ValueError:
        return None
    return int(parsed.timestamp() * 1000)
