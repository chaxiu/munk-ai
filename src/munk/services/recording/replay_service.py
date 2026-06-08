from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from munk.config.load import ResolvedConfig
from munk.recording import RecordingReplayResult, RecordingSession
from munk.runtime import build_case_request
from munk.services.operations.service import OperationService
from munk.services.running.service import RunService
from munk.testing import TestCase


class RecordingReplayService:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        operation_service: OperationService | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._operation_service = operation_service or OperationService()

    def replay_case(
        self,
        *,
        recording_id: str,
        session: RecordingSession,
        test_case: TestCase,
        test_case_path: Path,
    ) -> RecordingReplayResult:
        request_json: dict[str, Any] = {
            "recording_id": recording_id,
            "app_id": session.app_id,
            "case_id": test_case.case_id,
            "device_ref": session.device_ref,
            "entry_identity": session.app_target.entry_identity,
            "test_case_path": str(test_case_path),
        }
        tracker = self._operation_service.create_operation(
            kind="run_case",
            request_json=request_json,
            app_id=session.app_id,
            plan_id=self._plan_id_for(recording_id),
            case_id=test_case.case_id,
            requires_device=True,
            device_ref=session.device_ref,
        )
        tracker.mark_running(
            pid=os.getpid(),
            progress={
                "recording_id": recording_id,
                "status": "running",
                "case_id": test_case.case_id,
                "source_recording_case_path": str(test_case_path),
            },
        )
        tracker.append_event(
            event_type="recording_replay_started",
            message="recording replay started",
            data={"recording_id": recording_id, "case_id": test_case.case_id},
        )
        try:
            request = build_case_request(
                plan_id=self._plan_id_for(recording_id),
                app_id=session.app_id,
                case=test_case,
                app_target=session.app_target,
                device_ref=session.device_ref,
                artifact_path=test_case_path,
            )
            result = RunService(
                resolved_config=self._resolved_config,
                operation_tracker=tracker,
            ).execute_case(request)
        except Exception as exc:
            tracker.mark_failed(
                error_code="recording_replay_failed",
                error_message=str(exc),
                artifacts={
                    "source_recording_case_path": str(test_case_path),
                },
                progress={
                    "recording_id": recording_id,
                    "status": "failed",
                    "case_id": test_case.case_id,
                },
            )
            raise

        replay_result = RecordingReplayResult(
            recording_id=recording_id,
            case_id=test_case.case_id,
            operation_id=tracker.operation_id,
            run_dir=result.run_dir,
            result_path=Path(result.artifacts["result"]),
            artifact_manifest_path=Path(result.artifacts["artifact_manifest"]),
            verdict=result.verdict,
        )
        tracker.update_artifacts(
            {
                **result.artifacts,
                "source_recording_id": recording_id,
                "source_recording_case_path": str(test_case_path),
            }
        )
        tracker.append_event(
            event_type="recording_replay_completed",
            message="recording replay completed",
            data={
                "recording_id": recording_id,
                "case_id": test_case.case_id,
                "verdict": result.verdict,
                "run_dir": str(result.run_dir),
            },
        )
        tracker.mark_succeeded(
            verification_verdict=result.verdict,
            result_json={
                **result.model_dump(mode="json"),
                "recording_id": recording_id,
            },
            artifacts={
                **result.artifacts,
                "source_recording_id": recording_id,
                "source_recording_case_path": str(test_case_path),
            },
            progress={
                "recording_id": recording_id,
                "status": "completed",
                "case_id": test_case.case_id,
                "verification_verdict": result.verdict,
            },
        )
        return replay_result

    @staticmethod
    def _plan_id_for(recording_id: str) -> str:
        return f"recording-replay:{recording_id}"
