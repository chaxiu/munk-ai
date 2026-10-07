from __future__ import annotations

from .helpers import capture_interactive_observation
from .models import InteractiveObservation
from .session_service import InteractiveSessionService


class InteractiveObservationService:
    def __init__(self, session_service: InteractiveSessionService) -> None:
        self._session_service = session_service

    def observe(self, session_id: str) -> InteractiveObservation:
        entry = self._session_service.begin_observation(session_id)
        observation = capture_interactive_observation(
            session_id=session_id,
            context=entry.context,
        )
        return self._session_service.record_observation_step(session_id, observation)
