from __future__ import annotations

from .models import InteractiveFinalizeResult
from .session_service import InteractiveSessionService


class InteractiveReportService:
    def __init__(self, session_service: InteractiveSessionService) -> None:
        self._session_service = session_service

    def build_transcript(self, session_id: str) -> list[str]:
        session = self._session_service.get_session(session_id)
        return [step.summary for step in session.steps]

    def finalize(
        self,
        session_id: str,
        summary: str | None = None,
    ) -> InteractiveFinalizeResult:
        session = self._session_service.finalize_session(session_id)
        result = InteractiveFinalizeResult(
            session_id=session.session_id,
            status=session.status,
            platform=session.platform,
            device_ref=session.device_ref,
            step_count=session.step_count,
            steps_summary=self.build_transcript(session_id),
            last_observation_summary=(
                session.last_observation.summary
                if session.last_observation is not None
                else None
            ),
            agent_summary=summary,
        )
        session.finalized_result = result
        return result

