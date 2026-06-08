from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from munk.services.interactive.models import InteractiveSession

from .session_context import InteractiveSessionContext


@dataclass
class InteractiveSessionEntry:
    session: InteractiveSession
    context: InteractiveSessionContext


class InteractiveSessionRegistry:
    def __init__(self) -> None:
        self._active_entries: dict[str, InteractiveSessionEntry] = {}
        self._completed_sessions: dict[str, InteractiveSession] = {}

    def create(self, entry: InteractiveSessionEntry) -> InteractiveSession:
        session_id = entry.session.session_id
        if session_id in self._active_entries or session_id in self._completed_sessions:
            raise ValueError(f"interactive session already exists: {session_id}")
        self._active_entries[session_id] = entry
        return entry.session

    def get_active_entry(self, session_id: str) -> InteractiveSessionEntry:
        try:
            return self._active_entries[session_id]
        except KeyError as exc:
            raise LookupError(f"interactive session not found: {session_id}") from exc

    def get_entry(self, session_id: str) -> InteractiveSessionEntry:
        return self.get_active_entry(session_id)

    def get_any_session(self, session_id: str) -> InteractiveSession:
        entry = self._active_entries.get(session_id)
        if entry is not None:
            return entry.session
        completed = self._completed_sessions.get(session_id)
        if completed is not None:
            return completed
        raise LookupError(f"interactive session not found: {session_id}")

    def get(self, session_id: str) -> InteractiveSession:
        return self.get_any_session(session_id)

    def complete(self, session: InteractiveSession) -> None:
        self._active_entries.pop(session.session_id, None)
        self._completed_sessions[session.session_id] = session

    def delete(self, session_id: str) -> None:
        if session_id in self._active_entries:
            del self._active_entries[session_id]
            return
        if session_id in self._completed_sessions:
            del self._completed_sessions[session_id]
            return
        raise LookupError(f"interactive session not found: {session_id}")

    def sweep_expired(self, now: str) -> list[InteractiveSessionEntry]:
        now_dt = datetime.fromisoformat(now)
        expired_ids = [
            session_id
            for session_id, entry in self._active_entries.items()
            if datetime.fromisoformat(entry.session.expires_at) <= now_dt
            or datetime.fromisoformat(entry.session.idle_expires_at) <= now_dt
        ]
        expired_entries: list[InteractiveSessionEntry] = []
        for session_id in expired_ids:
            expired_entries.append(self._active_entries.pop(session_id))
        return expired_entries

    def list_active(self) -> list[InteractiveSession]:
        return [entry.session for entry in self._active_entries.values()]
