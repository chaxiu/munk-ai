from __future__ import annotations

from typing import Any, Callable, cast

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from munk.adapters.local_api.response_models import (
    ErrorResponse,
    OperationSubmissionData,
    RecordingAnalysisData,
    RecordingBeginData,
    RecordingCreateData,
    RecordingExportData,
    RecordingGetData,
    RecordingInteractionData,
    RecordingObservationData,
    RecordingReplayData,
    RecordingSessionData,
    RecordingTapData,
    RecordingTimelineData,
    SuccessResponse,
)
from munk.recording import (
    RecordingAnalysisResult,
    RecordingCaseExport,
    RecordingInteractionContractError,
    RecordingReplayResult,
    RecordingSessionNotFoundError,
    RecordingSessionStateError,
)
from munk.services.errors import DeviceConflictError
from munk.services.machine_contracts import MachineCommandResponse, build_error_result, build_success_result
from munk.services.recording.bridge_manager import RecordingBridgeError
from munk.services.recording.session_service import RecordingSessionService

from .recording_models import CreateRecordingRequest, ObserveTapRequest, RecordInteractionRequest


def build_recording_router(
    *,
    service_factory: Callable[[], RecordingSessionService],
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/v1/recordings",
        response_model=SuccessResponse[RecordingCreateData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def create_recording(request: CreateRecordingRequest, response: Response) -> dict[str, object] | JSONResponse:
        try:
            session = service_factory().create_session(
                app_target=request.app_target,
                device_ref=request.device_ref,
                case_id=request.case_id,
            )
            result = build_success_result(
                command="recordings_create",
                data={"session": _session_payload(session)},
            )
        except Exception as exc:
            return _error_response("recordings_create", exc)
        return _success_response(response, result)

    @router.post(
        "/v1/recordings/{recording_id}/begin",
        response_model=SuccessResponse[RecordingBeginData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def begin_recording(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            session, bridge_session = service_factory().begin_session(recording_id)
            result = build_success_result(
                command="recordings_begin",
                data={
                    "session": _session_payload(session),
                    "bridge": {
                        "recording_id": bridge_session.recording_id,
                        "base_url": bridge_session.base_url,
                        "ws_url": bridge_session.ws_url,
                    },
                },
            )
        except Exception as exc:
            return _error_response("recordings_begin", exc)
        return _success_response(response, result)

    @router.get(
        "/v1/recordings/{recording_id}",
        response_model=SuccessResponse[RecordingGetData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def get_recording(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            session = service_factory().get_session(recording_id)
            events = service_factory().list_recorded_events(recording_id)
            timeline = service_factory().list_timeline(recording_id)
            result = build_success_result(
                command="recordings_get",
                data={
                    "session": _session_payload(session),
                    "events": [_event_payload(event) for event in events],
                    "timeline": [_timeline_payload(entry) for entry in timeline],
                },
            )
        except Exception as exc:
            return _error_response("recordings_get", exc)
        return _success_response(response, result)

    @router.post(
        "/v1/recordings/{recording_id}/events/tap",
        response_model=SuccessResponse[RecordingTapData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def observe_tap(recording_id: str, request: ObserveTapRequest, response: Response) -> dict[str, object] | JSONResponse:
        try:
            event = service_factory().observe_tap(recording_id, request.to_command())
            result = build_success_result(
                command="recordings_tap",
                data={"event": _event_payload(event)},
            )
        except Exception as exc:
            return _error_response("recordings_tap", exc)
        return _success_response(response, result)

    @router.post(
        "/v1/recordings/{recording_id}/events",
        response_model=SuccessResponse[RecordingInteractionData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def record_interaction(
        recording_id: str, request: RecordInteractionRequest, response: Response
    ) -> dict[str, object] | JSONResponse:
        try:
            entry = service_factory().record_interaction(recording_id, request.to_command())
            result = build_success_result(
                command="recordings_event_record",
                data={"entry": _timeline_payload(entry)},
            )
        except Exception as exc:
            return _error_response("recordings_event_record", exc)
        return _success_response(response, result)

    @router.get(
        "/v1/recordings/{recording_id}/timeline",
        response_model=SuccessResponse[RecordingTimelineData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def get_recording_timeline(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            timeline = service_factory().list_timeline(recording_id)
            result = build_success_result(
                command="recordings_timeline_get",
                data={"timeline": [_timeline_payload(entry) for entry in timeline]},
            )
        except Exception as exc:
            return _error_response("recordings_timeline_get", exc)
        return _success_response(response, result)

    @router.get(
        "/v1/recordings/{recording_id}/observations/{observation_id}",
        response_model=SuccessResponse[RecordingObservationData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def get_recording_observation(
        recording_id: str, observation_id: str, response: Response
    ) -> dict[str, object] | JSONResponse:
        try:
            observation = service_factory().get_observation(recording_id, observation_id)
            result = build_success_result(
                command="recordings_observation_get",
                data={"observation": observation.model_dump(mode="json")},
            )
        except Exception as exc:
            return _error_response("recordings_observation_get", exc)
        return _success_response(response, result)

    @router.get(
        "/v1/recordings/{recording_id}/analysis",
        response_model=SuccessResponse[RecordingAnalysisData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def analyze_recording(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            analysis = service_factory().get_analysis(recording_id)
            operation = service_factory().get_active_analysis_operation(recording_id)
            if analysis is None:
                analysis = RecordingAnalysisResult(recording_id=recording_id, status="pending")
                if operation is None:
                    analysis = analysis.model_copy(update={"warnings": ["analysis_not_started"]})
            result = build_success_result(
                command="recordings_analysis_get",
                data={
                    "analysis": _analysis_payload(analysis),
                    "operation": _operation_payload(operation),
                },
            )
        except Exception as exc:
            return _error_response("recordings_analysis_get", exc)
        return _success_response(response, result)

    @router.post(
        "/v1/recordings/{recording_id}/analysis",
        response_model=SuccessResponse[OperationSubmissionData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def submit_recording_analysis(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            operation = service_factory().submit_analysis(recording_id)
            result = build_success_result(
                command="recordings_analysis_submit",
                data={
                    "operation_id": operation.operation_id,
                    "status": operation.status,
                    "app_id": operation.app_id,
                    "phase": cast(dict[str, Any], operation.progress_json).get("phase"),
                },
            )
        except Exception as exc:
            return _error_response("recordings_analysis_submit", exc)
        return _success_response(response, result)

    @router.post(
        "/v1/recordings/{recording_id}/export-case",
        response_model=SuccessResponse[RecordingExportData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def export_recording_case(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            analysis, export_result = service_factory().export_case_with_analysis(recording_id)
            result = build_success_result(
                command="recordings_export_case",
                data={
                    "analysis": _analysis_payload(analysis),
                    "case": _export_payload(export_result),
                    "artifacts": {
                        "analysis_json": str(export_result.analysis_path),
                        "test_case_json": str(export_result.case_path),
                        **(
                            {"plan_json": str(export_result.plan_path)}
                            if export_result.plan_path is not None
                            else {}
                        ),
                        **(
                            {"plan_snapshot": str(export_result.snapshot_path)}
                            if export_result.snapshot_path is not None
                            else {}
                        ),
                    },
                },
            )
        except Exception as exc:
            return _error_response("recordings_export_case", exc)
        return _success_response(response, result)

    @router.post(
        "/v1/recordings/{recording_id}/replay-case",
        response_model=SuccessResponse[RecordingReplayData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def replay_recording_case(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            replay_result = service_factory().replay_case(recording_id)
            result = build_success_result(
                command="recordings_replay_case",
                data={"replay": _replay_payload(replay_result)},
                artifacts={
                    "run_dir": str(replay_result.run_dir),
                    "result": str(replay_result.result_path),
                    "artifact_manifest": str(replay_result.artifact_manifest_path),
                },
            )
        except Exception as exc:
            return _error_response("recordings_replay_case", exc)
        return _success_response(response, result)

    @router.post(
        "/v1/recordings/{recording_id}/stop",
        response_model=SuccessResponse[RecordingSessionData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def stop_recording(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            session = service_factory().stop_session(recording_id)
            result = build_success_result(
                command="recordings_stop",
                data={"session": _session_payload(session)},
            )
        except Exception as exc:
            return _error_response("recordings_stop", exc)
        return _success_response(response, result)

    @router.post(
        "/v1/recordings/{recording_id}/cancel",
        response_model=SuccessResponse[RecordingSessionData],
        responses=_recording_error_responses(404, 409, 422, 503, 500),
    )
    def cancel_recording(recording_id: str, response: Response) -> dict[str, object] | JSONResponse:
        try:
            session = service_factory().cancel_session(recording_id)
            result = build_success_result(
                command="recordings_cancel",
                data={"session": _session_payload(session)},
            )
        except Exception as exc:
            return _error_response("recordings_cancel", exc)
        return _success_response(response, result)

    return router


def _recording_error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    return {status_code: {"model": ErrorResponse} for status_code in status_codes}


def _success_response(response: Response, result: MachineCommandResponse) -> dict[str, object]:
    response.status_code = result.http_status
    return result.payload


def _error_response(command: str, exc: Exception) -> JSONResponse:
    if isinstance(exc, RecordingBridgeError):
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "recording_bridge_unavailable",
                    "message": str(exc),
                },
            },
        )
    if isinstance(exc, RecordingSessionNotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "recording_session_not_found",
                    "message": str(exc),
                },
            },
        )
    if isinstance(exc, RecordingSessionStateError):
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "recording_invalid_state",
                    "message": str(exc),
                },
            },
        )
    if isinstance(exc, RecordingInteractionContractError):
        return JSONResponse(
            status_code=422,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "invalid_recording_interaction_contract",
                    "message": str(exc),
                },
            },
        )
    if isinstance(exc, RuntimeError) and "analysis" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "recording_analysis_unavailable",
                    "message": str(exc),
                },
            },
        )
    if isinstance(exc, RuntimeError) and "replay" in str(exc).lower():
        return JSONResponse(
            status_code=503,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "recording_replay_unavailable",
                    "message": str(exc),
                },
            },
        )
    if isinstance(exc, DeviceConflictError):
        return JSONResponse(
            status_code=409,
            content={
                "ok": False,
                "command": command,
                "error": {
                    "code": "device_conflict",
                    "message": str(exc),
                    "details": exc.to_details(),
                },
            },
        )
    response = build_error_result(command=command, exc=exc)
    return JSONResponse(status_code=response.http_status, content=response.payload)


def _session_payload(session) -> dict[str, object]:  # noqa: ANN001
    return session.model_dump(mode="json")


def _event_payload(event) -> dict[str, object]:  # noqa: ANN001
    return event.model_dump(mode="json")


def _timeline_payload(entry) -> dict[str, object]:  # noqa: ANN001
    return entry.model_dump(mode="json")


def _analysis_payload(analysis: RecordingAnalysisResult) -> dict[str, object]:
    return analysis.model_dump(mode="json")


def _operation_payload(operation) -> dict[str, object] | None:  # noqa: ANN001
    if operation is None:
        return None
    progress = cast(dict[str, Any], operation.progress_json) if isinstance(operation.progress_json, dict) else {}
    return {
        "operation_id": operation.operation_id,
        "status": operation.status,
        "app_id": operation.app_id,
        "phase": progress.get("phase"),
    }


def _export_payload(export_result: RecordingCaseExport) -> dict[str, object]:
    return export_result.model_dump(mode="json")


def _replay_payload(replay_result: RecordingReplayResult) -> dict[str, object]:
    return replay_result.model_dump(mode="json")
