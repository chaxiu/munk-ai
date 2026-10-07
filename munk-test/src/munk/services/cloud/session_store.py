from __future__ import annotations

import json
import os
from pathlib import Path

from munk.services.cloud.auth_models import CloudSessionRecord, PendingCloudLogin
from munk.user_data import munkai_home


def cloud_home(*, home: Path | None = None) -> Path:
    root = home if home is not None else munkai_home()
    return root / "cloud"


def cloud_session_path(*, home: Path | None = None) -> Path:
    return cloud_home(home=home) / "session.json"


def cloud_pending_login_path(*, home: Path | None = None) -> Path:
    return cloud_home(home=home) / "pending_login.json"


class CloudSessionStore:
    def __init__(self, *, home: Path | None = None) -> None:
        self._home = home.resolve() if home is not None else None

    @property
    def session_path(self) -> Path:
        return cloud_session_path(home=self._home)

    @property
    def pending_path(self) -> Path:
        return cloud_pending_login_path(home=self._home)

    def load_session(self) -> CloudSessionRecord | None:
        path = self.session_path
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"cloud session root must be an object: {path}")
        return CloudSessionRecord.model_validate(raw)

    def save_session(self, session: CloudSessionRecord) -> None:
        path = self.session_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = session.model_dump(mode="json")
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def clear_session(self) -> None:
        path = self.session_path
        if path.exists():
            path.unlink()

    def load_pending(self) -> PendingCloudLogin | None:
        path = self.pending_path
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"pending login root must be an object: {path}")
        return PendingCloudLogin.model_validate(raw)

    def save_pending(self, pending: PendingCloudLogin) -> None:
        path = self.pending_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(pending.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def clear_pending(self) -> None:
        path = self.pending_path
        if path.exists():
            path.unlink()
