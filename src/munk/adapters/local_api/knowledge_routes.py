from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from munk.adapters.local_api.response_models import ErrorResponse, SuccessResponse
from munk.app_assets.service import AppAssetService
from munk.app_knowledge import KnowledgeCardStatus, KnowledgeCardType
from munk.services.knowledge import KnowledgeCandidateApprovalService, KnowledgeCardService

from .knowledge_models import (
    KnowledgeCandidateApproveData,
    KnowledgeCandidateDecisionRequest,
    KnowledgeCandidateListData,
    KnowledgeCandidateRejectData,
    KnowledgeCardDeleteData,
    KnowledgeCardGetData,
    KnowledgeCardListData,
    KnowledgeCardMutationData,
    KnowledgeCardWriteRequest,
)
from .route_helpers import error_response

_KNOWLEDGE_ERROR_RESPONSES = cast(
    dict[int | str, dict[str, Any]],
    {
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


def build_knowledge_router(
    *,
    service_factory: Callable[[], KnowledgeCandidateApprovalService] | None = None,
    card_service_factory: Callable[[], KnowledgeCardService] | None = None,
) -> APIRouter:
    router = APIRouter()

    def get_service() -> KnowledgeCandidateApprovalService:
        if service_factory is not None:
            return service_factory()
        app_service = AppAssetService()
        return KnowledgeCandidateApprovalService(assets_root=app_service.app_registry.root_dir)

    def get_card_service() -> KnowledgeCardService:
        if card_service_factory is not None:
            return card_service_factory()
        app_service = AppAssetService()
        return KnowledgeCardService(assets_root=app_service.app_registry.root_dir)

    @router.get(
        "/v1/apps/{app_id}/knowledge/candidates",
        response_model=SuccessResponse[KnowledgeCandidateListData],
        responses=_KNOWLEDGE_ERROR_RESPONSES,
    )
    def list_candidates(
        app_id: str,
        response: Response,
        status: str | None = Query(None),
        candidate_id: str | None = Query(None),
        limit: int = Query(20, ge=1, le=200),
    ) -> dict[str, object] | JSONResponse:
        service = get_service()
        try:
            result = service.list_candidates(
                app_id=app_id,
                status=status,
                candidate_id=candidate_id,
                limit=limit,
            )
        except FileNotFoundError:
            return _error_response(404, "knowledge_candidates_list", "app_not_found", f"app '{app_id}' not found")
        except ValueError as exc:
            return _error_response(422, "knowledge_candidates_list", "candidate_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "knowledge_candidates_list", "knowledge_candidates_list_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "knowledge_candidates_list",
            "data": KnowledgeCandidateListData(
                items=list(result.items),
                total_count=result.total_count,
            ).model_dump(mode="json"),
        }

    @router.post(
        "/v1/apps/{app_id}/knowledge/candidates/{candidate_id}/approve",
        response_model=SuccessResponse[KnowledgeCandidateApproveData],
        responses=_KNOWLEDGE_ERROR_RESPONSES,
    )
    def approve_candidate(
        app_id: str,
        candidate_id: str,
        request: KnowledgeCandidateDecisionRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        service = get_service()
        try:
            result = service.approve_candidate(
                app_id=app_id,
                candidate_id=candidate_id,
                reviewed_by=request.reviewed_by,
                review_note=request.review_note,
            )
        except FileNotFoundError as exc:
            message = str(exc)
            code = "candidate_not_found" if "candidate" in message else "app_not_found"
            return _error_response(404, "knowledge_candidates_approve", code, message)
        except ValueError as exc:
            return _error_response(422, "knowledge_candidates_approve", "candidate_approval_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "knowledge_candidates_approve", "knowledge_candidates_approve_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "knowledge_candidates_approve",
            "data": KnowledgeCandidateApproveData(**result.model_dump(mode="json")).model_dump(mode="json"),
        }

    @router.post(
        "/v1/apps/{app_id}/knowledge/candidates/{candidate_id}/reject",
        response_model=SuccessResponse[KnowledgeCandidateRejectData],
        responses=_KNOWLEDGE_ERROR_RESPONSES,
    )
    def reject_candidate(
        app_id: str,
        candidate_id: str,
        request: KnowledgeCandidateDecisionRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        service = get_service()
        try:
            result = service.reject_candidate(
                app_id=app_id,
                candidate_id=candidate_id,
                reviewed_by=request.reviewed_by,
                review_note=request.review_note,
            )
        except FileNotFoundError as exc:
            message = str(exc)
            code = "candidate_not_found" if "candidate" in message else "app_not_found"
            return _error_response(404, "knowledge_candidates_reject", code, message)
        except ValueError as exc:
            return _error_response(422, "knowledge_candidates_reject", "candidate_rejection_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "knowledge_candidates_reject", "knowledge_candidates_reject_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "knowledge_candidates_reject",
            "data": KnowledgeCandidateRejectData(**result.model_dump(mode="json")).model_dump(mode="json"),
        }

    @router.get(
        "/v1/apps/{app_id}/knowledge/cards",
        response_model=SuccessResponse[KnowledgeCardListData],
        responses=_KNOWLEDGE_ERROR_RESPONSES,
    )
    def list_cards(
        app_id: str,
        response: Response,
        q: str | None = Query(None),
        card_type: KnowledgeCardType | None = Query(None),
        status: KnowledgeCardStatus | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> dict[str, object] | JSONResponse:
        service = get_card_service()
        try:
            result = service.list_cards(
                app_id=app_id,
                query=q,
                card_type=card_type,
                status=status,
                limit=limit,
                offset=offset,
            )
        except FileNotFoundError:
            return _error_response(404, "knowledge_cards_list", "app_not_found", f"app '{app_id}' not found")
        except ValueError as exc:
            return _error_response(422, "knowledge_cards_list", "knowledge_card_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "knowledge_cards_list", "knowledge_cards_list_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "knowledge_cards_list",
            "data": KnowledgeCardListData(
                items=list(result.items),
                total_count=result.total_count,
                limit=result.limit,
                offset=result.offset,
            ).model_dump(mode="json"),
        }

    @router.get(
        "/v1/apps/{app_id}/knowledge/cards/{card_id}",
        response_model=SuccessResponse[KnowledgeCardGetData],
        responses=_KNOWLEDGE_ERROR_RESPONSES,
    )
    def get_card(
        app_id: str,
        card_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        service = get_card_service()
        try:
            card = service.get_card(app_id=app_id, card_id=card_id)
        except FileNotFoundError as exc:
            return _knowledge_not_found_response(command="knowledge_cards_get", app_id=app_id, exc=exc)
        except ValueError as exc:
            return _error_response(422, "knowledge_cards_get", "knowledge_card_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "knowledge_cards_get", "knowledge_cards_get_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "knowledge_cards_get",
            "data": KnowledgeCardGetData(card=card).model_dump(mode="json"),
        }

    @router.post(
        "/v1/apps/{app_id}/knowledge/cards",
        response_model=SuccessResponse[KnowledgeCardMutationData],
        responses=_KNOWLEDGE_ERROR_RESPONSES,
    )
    def create_card(
        app_id: str,
        request: KnowledgeCardWriteRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        service = get_card_service()
        try:
            result = service.create_card(app_id=app_id, card=request.card)
        except FileNotFoundError as exc:
            return _knowledge_not_found_response(command="knowledge_cards_create", app_id=app_id, exc=exc)
        except ValueError as exc:
            return _error_response(422, "knowledge_cards_create", "knowledge_card_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "knowledge_cards_create", "knowledge_cards_create_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "knowledge_cards_create",
            "data": _mutation_data(result).model_dump(mode="json"),
        }

    @router.put(
        "/v1/apps/{app_id}/knowledge/cards/{card_id}",
        response_model=SuccessResponse[KnowledgeCardMutationData],
        responses=_KNOWLEDGE_ERROR_RESPONSES,
    )
    def update_card(
        app_id: str,
        card_id: str,
        request: KnowledgeCardWriteRequest,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        service = get_card_service()
        try:
            result = service.update_card(app_id=app_id, card_id=card_id, card=request.card)
        except FileNotFoundError as exc:
            return _knowledge_not_found_response(command="knowledge_cards_update", app_id=app_id, exc=exc)
        except ValueError as exc:
            return _error_response(422, "knowledge_cards_update", "knowledge_card_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "knowledge_cards_update", "knowledge_cards_update_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "knowledge_cards_update",
            "data": _mutation_data(result).model_dump(mode="json"),
        }

    @router.delete(
        "/v1/apps/{app_id}/knowledge/cards/{card_id}",
        response_model=SuccessResponse[KnowledgeCardDeleteData],
        responses=_KNOWLEDGE_ERROR_RESPONSES,
    )
    def delete_card(
        app_id: str,
        card_id: str,
        response: Response,
    ) -> dict[str, object] | JSONResponse:
        service = get_card_service()
        try:
            result = service.delete_card(app_id=app_id, card_id=card_id)
        except FileNotFoundError as exc:
            return _knowledge_not_found_response(command="knowledge_cards_delete", app_id=app_id, exc=exc)
        except ValueError as exc:
            return _error_response(422, "knowledge_cards_delete", "knowledge_card_validation_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return _error_response(500, "knowledge_cards_delete", "knowledge_cards_delete_failed", str(exc))
        response.status_code = 200
        return {
            "ok": True,
            "command": "knowledge_cards_delete",
            "data": KnowledgeCardDeleteData(
                deleted_card_id=result.deleted_card_id,
                build_manifest_path=result.build_result.build_manifest_path,
                db_path=result.build_result.db_path,
                total_cards=result.build_result.total_cards,
                rebuilt_cards=result.build_result.rebuilt_cards,
                skipped_cards=result.build_result.skipped_cards,
                cache_hit=result.build_result.cache_hit,
            ).model_dump(mode="json"),
        }

    return router


def _error_response(status_code: int, command: str, code: str, message: str) -> JSONResponse:
    return error_response(
        status_code=status_code,
        command=command,
        code=code,
        message=message,
    )


def _knowledge_not_found_response(*, command: str, app_id: str, exc: FileNotFoundError) -> JSONResponse:
    message = str(exc)
    code = "app_not_found" if "AppProfile not found" in message else "card_not_found"
    if code == "app_not_found":
        message = f"app '{app_id}' not found"
    return _error_response(404, command, code, message)


def _mutation_data(result: Any) -> KnowledgeCardMutationData:
    return KnowledgeCardMutationData(
        card=result.card,
        build_manifest_path=result.build_result.build_manifest_path,
        db_path=result.build_result.db_path,
        total_cards=result.build_result.total_cards,
        rebuilt_cards=result.build_result.rebuilt_cards,
        skipped_cards=result.build_result.skipped_cards,
        cache_hit=result.build_result.cache_hit,
    )
