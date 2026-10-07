from __future__ import annotations

import json
import os
from pathlib import Path

from munk.services.cloud.session_store import cloud_home
from munk.services.cloud.sync_models import CloudLink, CloudLinksState


def cloud_links_path(*, home: Path | None = None) -> Path:
    return cloud_home(home=home) / "links.json"


def sync_state_key(workspace_id: str, app_id: str) -> str:
    return f"{workspace_id}/{app_id}"


class CloudLinkStore:
    def __init__(self, *, home: Path | None = None) -> None:
        self._home = home.resolve() if home is not None else None

    @property
    def path(self) -> Path:
        return cloud_links_path(home=self._home)

    def load(self) -> CloudLinksState:
        path = self.path
        if not path.exists():
            return CloudLinksState()
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"cloud links root must be an object: {path}")
        return CloudLinksState.model_validate(raw)

    def save(self, state: CloudLinksState) -> None:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(state.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def get_active(self) -> CloudLink | None:
        state = self.load()
        if not state.active_app_id:
            return None
        for item in state.items:
            if item.app_id == state.active_app_id:
                return item
        return None

    def upsert_link(self, link: CloudLink, *, make_active: bool = True) -> CloudLinksState:
        state = self.load()
        items = [item for item in state.items if item.app_id != link.app_id]
        items.append(link)
        active = link.app_id if make_active else state.active_app_id
        if active is not None and not any(item.app_id == active for item in items):
            active = link.app_id if make_active else (items[0].app_id if items else None)
        next_state = CloudLinksState(items=items, active_app_id=active)
        self.save(next_state)
        return next_state

    def remove_link(self, app_id: str) -> tuple[CloudLinksState, CloudLink | None]:
        state = self.load()
        removed: CloudLink | None = None
        items: list[CloudLink] = []
        for item in state.items:
            if item.app_id == app_id:
                removed = item
                continue
            items.append(item)
        active = state.active_app_id
        if active == app_id:
            active = items[0].app_id if items else None
        next_state = CloudLinksState(items=items, active_app_id=active)
        self.save(next_state)
        return next_state, removed

    def set_active(self, app_id: str) -> CloudLinksState:
        state = self.load()
        if not any(item.app_id == app_id for item in state.items):
            raise KeyError(app_id)
        next_state = CloudLinksState(items=list(state.items), active_app_id=app_id)
        self.save(next_state)
        return next_state

    def clear(self) -> None:
        path = self.path
        if path.exists():
            path.unlink()
