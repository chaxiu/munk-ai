from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin

import httpx

from munk.network.proxy import ResolvedProxyConfig, build_httpx_proxy_kwargs
from munk.services.cloud.auth_models import (
    CloudBffError,
    CloudUserSummary,
    CloudWorkspaceSummary,
)
from munk.services.cloud.sync_models import (
    AppSyncBundle,
    CloudAppEnsureResult,
    CloudAppSummary,
    CloudSyncPushResult,
)

DEFAULT_CLOUD_BASE_URL = "https://www.munk.sh"
ENV_CLOUD_BASE_URL = "MUNK_CLOUD_BASE_URL"
_HTTP_ERROR_STATUS_FLOOR = 400


def resolve_cloud_base_url(explicit: str | None = None) -> str:
    raw = (explicit or os.environ.get(ENV_CLOUD_BASE_URL) or DEFAULT_CLOUD_BASE_URL).strip()
    return raw.rstrip("/")


class CloudBffClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_sec: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        proxy: ResolvedProxyConfig | None = None,
    ) -> None:
        self._base_url = resolve_cloud_base_url(base_url)
        self._timeout_sec = timeout_sec
        self._transport = transport
        self._proxy = proxy

    @property
    def base_url(self) -> str:
        return self._base_url

    def build_local_authorize_url(self, *, redirect_uri: str, state: str) -> str:
        params = httpx.QueryParams(
            {
                "client": "local",
                "redirect_uri": redirect_uri,
                "state": state,
            }
        )
        return f"{self._base_url}/login?{params}"

    def exchange_handoff(
        self,
        *,
        handoff_code: str,
        redirect_uri: str,
        state: str,
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/api/cloud/auth/handoff/exchange",
            json_body={
                "handoff_code": handoff_code,
                "redirect_uri": redirect_uri,
                "state": state,
            },
        )

    def refresh(self, *, refresh_token: str) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/api/cloud/auth/refresh",
            json_body={"refresh_token": refresh_token},
        )

    def list_workspaces(self, *, access_token: str) -> list[CloudWorkspaceSummary]:
        payload = self._request_json(
            "GET",
            "/api/cloud/auth/workspaces",
            access_token=access_token,
        )
        rows = payload.get("workspaces") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise CloudBffError(
                status_code=500,
                code="invalid_workspaces_response",
                message="Cloud BFF workspaces response was invalid.",
            )
        return [CloudWorkspaceSummary.model_validate(item) for item in rows]

    def list_apps(self, *, access_token: str, workspace_id: str) -> list[CloudAppSummary]:
        payload = self._request_json(
            "GET",
            "/api/cloud/apps",
            access_token=access_token,
            params={"workspace_id": workspace_id},
        )
        rows = payload.get("apps") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise CloudBffError(
                status_code=500,
                code="invalid_apps_response",
                message="Cloud BFF apps response was invalid.",
            )
        return [CloudAppSummary.model_validate(item) for item in rows]

    def ensure_app(
        self,
        *,
        access_token: str,
        workspace_id: str,
        app_id: str,
        platform: str,
        app_name: str | None = None,
        app_introduction_ref: str | None = None,
        app_knowledge_ref: str | None = None,
        android: dict[str, Any] | None = None,
        ios: dict[str, Any] | None = None,
        web: dict[str, Any] | None = None,
    ) -> CloudAppEnsureResult:
        body: dict[str, Any] = {
            "workspace_id": workspace_id,
            "app_id": app_id,
            "platform": platform,
            "app_name": app_name,
        }
        if app_introduction_ref is not None:
            body["app_introduction_ref"] = app_introduction_ref
        if app_knowledge_ref is not None:
            body["app_knowledge_ref"] = app_knowledge_ref
        if android is not None:
            body["android"] = android
        if ios is not None:
            body["ios"] = ios
        if web is not None:
            body["web"] = web
        payload = self._request_json(
            "POST",
            "/api/cloud/apps/ensure",
            access_token=access_token,
            json_body=body,
        )
        return CloudAppEnsureResult.model_validate(payload)

    def sync_status(
        self,
        *,
        access_token: str,
        workspace_id: str,
        app_id: str,
    ) -> dict[str, Any]:
        return self._request_json(
            "GET",
            "/api/cloud/sync/status",
            access_token=access_token,
            params={"workspace_id": workspace_id, "app_id": app_id},
        )

    def sync_pull(
        self,
        *,
        access_token: str,
        workspace_id: str,
        app_id: str,
    ) -> AppSyncBundle:
        payload = self._request_json(
            "POST",
            "/api/cloud/sync/pull",
            access_token=access_token,
            json_body={"workspace_id": workspace_id, "app_id": app_id},
        )
        return AppSyncBundle.model_validate(payload)

    def sync_push(
        self,
        *,
        access_token: str,
        workspace_id: str,
        app_id: str,
        expected_revision: int,
        app_profile: dict[str, Any],
        plans: list[Any],
        content_hash: str | None = None,
        introduction: str | None = None,
        knowledge_document: dict[str, Any] | None = None,
        team_config: dict[str, Any] | None = None,
    ) -> CloudSyncPushResult:
        return self._sync_write(
            path="/api/cloud/sync/push",
            access_token=access_token,
            workspace_id=workspace_id,
            app_id=app_id,
            expected_revision=expected_revision,
            app_profile=app_profile,
            plans=plans,
            content_hash=content_hash,
            introduction=introduction,
            knowledge_document=knowledge_document,
            team_config=team_config,
        )

    def sync_force_push(
        self,
        *,
        access_token: str,
        workspace_id: str,
        app_id: str,
        expected_revision: int,
        app_profile: dict[str, Any],
        plans: list[Any],
        content_hash: str | None = None,
        introduction: str | None = None,
        knowledge_document: dict[str, Any] | None = None,
        team_config: dict[str, Any] | None = None,
    ) -> CloudSyncPushResult:
        return self._sync_write(
            path="/api/cloud/sync/force-push",
            access_token=access_token,
            workspace_id=workspace_id,
            app_id=app_id,
            expected_revision=expected_revision,
            app_profile=app_profile,
            plans=plans,
            content_hash=content_hash,
            introduction=introduction,
            knowledge_document=knowledge_document,
            team_config=team_config,
        )

    def _sync_write(
        self,
        *,
        path: str,
        access_token: str,
        workspace_id: str,
        app_id: str,
        expected_revision: int,
        app_profile: dict[str, Any],
        plans: list[Any],
        content_hash: str | None,
        introduction: str | None,
        knowledge_document: dict[str, Any] | None,
        team_config: dict[str, Any] | None,
    ) -> CloudSyncPushResult:
        body: dict[str, Any] = {
            "workspace_id": workspace_id,
            "app_id": app_id,
            "expected_revision": expected_revision,
            "app_profile": app_profile,
            "plans": plans,
            "introduction": introduction,
            "knowledge_document": knowledge_document,
            "team_config": team_config if team_config is not None else {},
        }
        if content_hash is not None:
            body["content_hash"] = content_hash
        payload = self._request_json(
            "POST",
            path,
            access_token=access_token,
            json_body=body,
        )
        return CloudSyncPushResult.model_validate(payload)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        access_token: str | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = urljoin(f"{self._base_url}/", path.lstrip("/"))
        headers: dict[str, str] = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        # Always trust_env=False. Loopback (localhost / 127.0.0.1) bypasses proxy;
        # remote BFF (munk.sh) uses .munk/config.yaml proxy when enabled.
        client_kwargs: dict[str, Any] = {
            "timeout": self._timeout_sec,
            **build_httpx_proxy_kwargs(url=url, proxy=self._proxy),
        }
        if self._transport is not None:
            client_kwargs["transport"] = self._transport

        with httpx.Client(**client_kwargs) as client:
            response = client.request(
                method,
                url,
                json=json_body,
                headers=headers,
                params=params,
            )

        if response.status_code >= _HTTP_ERROR_STATUS_FLOOR:
            code = "cloud_bff_error"
            message = response.text.strip() or f"Cloud BFF request failed ({response.status_code})"
            details: Any = None
            try:
                body = response.json()
            except ValueError:
                body = None
            if isinstance(body, dict):
                data = body.get("data")
                if isinstance(data, dict) and isinstance(data.get("code"), str):
                    code = data["code"]
                status_message = body.get("statusMessage") or body.get("message")
                if isinstance(status_message, str) and status_message.strip():
                    message = status_message.strip()
                details = body
            raise CloudBffError(
                status_code=response.status_code,
                code=code,
                message=message,
                details=details,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise CloudBffError(
                status_code=500,
                code="invalid_json_response",
                message="Cloud BFF returned non-JSON response.",
            ) from exc
        if not isinstance(payload, dict):
            raise CloudBffError(
                status_code=500,
                code="invalid_json_response",
                message="Cloud BFF returned a non-object JSON payload.",
            )
        return payload


def parse_token_payload(payload: dict[str, Any]) -> tuple[str, str, str | None, CloudUserSummary]:
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise CloudBffError(
            status_code=500,
            code="invalid_token_payload",
            message="Cloud BFF token payload missing access_token.",
        )
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        raise CloudBffError(
            status_code=500,
            code="invalid_token_payload",
            message="Cloud BFF token payload missing refresh_token.",
        )
    expires_at = payload.get("expires_at")
    expires_at_text = expires_at.strip() if isinstance(expires_at, str) and expires_at.strip() else None
    user_raw = payload.get("user")
    if not isinstance(user_raw, dict):
        raise CloudBffError(
            status_code=500,
            code="invalid_token_payload",
            message="Cloud BFF token payload missing user.",
        )
    return access_token, refresh_token, expires_at_text, CloudUserSummary.model_validate(user_raw)
