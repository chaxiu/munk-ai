from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path


def debug_report_cold_start_settle(
    *,
    hypothesis_id: str,
    location: str,
    msg: str,
    data: dict[str, object],
) -> None:
    try:
        env_path = Path.cwd() / ".dbg" / "cold-start-settle.env"
        url = "http://127.0.0.1:7777/event"
        session_id = "cold-start-settle"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DEBUG_SERVER_URL="):
                    url = line.split("=", 1)[1].strip() or url
                elif line.startswith("DEBUG_SESSION_ID="):
                    session_id = line.split("=", 1)[1].strip() or session_id
        payload: dict[str, object] = {
            "sessionId": session_id,
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "msg": msg,
            "data": data,
            "ts": int(time.time() * 1000),
        }
        urllib.request.urlopen(
            urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            ),
            timeout=0.2,
        ).read()
    except Exception:
        pass
