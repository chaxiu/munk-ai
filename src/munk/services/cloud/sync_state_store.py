from __future__ import annotations

import json
import os
from pathlib import Path

from munk.services.cloud.link_store import sync_state_key
from munk.services.cloud.session_store import cloud_home
from munk.services.cloud.sync_models import CloudSyncState


def cloud_sync_states_path(*, home: Path | None = None) -> Path:
    return cloud_home(home=home) / "sync_states.json"


class CloudSyncStateStore:
    def __init__(self, *, home: Path | None = None) -> None:
        self._home = home.resolve() if home is not None else None

    @property
    def path(self) -> Path:
        return cloud_sync_states_path(home=self._home)

    def _load_map(self) -> dict[str, CloudSyncState]:
        path = self.path
        if not path.exists():
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"cloud sync_states root must be an object: {path}")
        out: dict[str, CloudSyncState] = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            out[key] = CloudSyncState.model_validate(value)
        return out

    def _save_map(self, states: dict[str, CloudSyncState]) -> None:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: state.model_dump(mode="json") for key, state in sorted(states.items())}
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def load(self, *, workspace_id: str, app_id: str) -> CloudSyncState | None:
        return self._load_map().get(sync_state_key(workspace_id, app_id))

    def save(self, state: CloudSyncState) -> None:
        states = self._load_map()
        states[sync_state_key(state.workspace_id, state.app_id)] = state
        self._save_map(states)

    def clear(self, *, workspace_id: str, app_id: str) -> None:
        states = self._load_map()
        key = sync_state_key(workspace_id, app_id)
        if key not in states:
            return
        del states[key]
        if states:
            self._save_map(states)
        else:
            self.clear_all()

    def clear_all(self) -> None:
        path = self.path
        if path.exists():
            path.unlink()
