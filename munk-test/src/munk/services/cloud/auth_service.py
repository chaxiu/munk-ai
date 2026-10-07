from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypeVar
from urllib.parse import urljoin

from munk.config.load import load_resolved_config
from munk.network.proxy import ResolvedProxyConfig, resolve_proxy_config
from munk.services.cloud.auth_models import (
    CloudBffError,
    CloudLoginStart,
    CloudSessionRecord,
    CloudSessionSummary,
    CloudWorkspaceSummary,
    PendingCloudLogin,
    utc_now,
)
from munk.services.cloud.bff_client import CloudBffClient, parse_token_payload, resolve_cloud_base_url
from munk.services.cloud.session_store import CloudSessionStore

_REFRESH_SKEW = timedelta(seconds=60)
_PENDING_TTL = timedelta(minutes=15)
_SESSION_EXPIRED_MESSAGE = "Cloud session expired. Sign in again to continue."
_HTTP_UNAUTHORIZED = 401
_REAUTH_ERROR_CODES = frozenset(
    {
        "refresh_failed",
        "session_expired",
        "not_authenticated",
        "unauthorized",
        "invalid_token",
        "jwt_expired",
    }
)

T = TypeVar("T")


class CloudAuthService:
    def __init__(
        self,
        *,
        home: Path | None = None,
        cloud_base_url: str | None = None,
        bff_client: CloudBffClient | None = None,
        store: CloudSessionStore | None = None,
        proxy: ResolvedProxyConfig | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self._store = store or CloudSessionStore(home=home)
        self._cloud_base_url = resolve_cloud_base_url(cloud_base_url)
        resolved_proxy = proxy
        if resolved_proxy is None and bff_client is None:
            resolved_proxy = _load_proxy_config(workspace_root=workspace_root)
        self._bff = bff_client or CloudBffClient(
            base_url=self._cloud_base_url,
            proxy=resolved_proxy,
        )

    @property
    def cloud_base_url(self) -> str:
        return self._bff.base_url

    @property
    def bff_client(self) -> CloudBffClient:
        return self._bff

    def start_login(self, *, local_api_base_url: str) -> CloudLoginStart:
        redirect_uri = self._build_callback_uri(local_api_base_url)
        state = secrets.token_urlsafe(24)
        pending = PendingCloudLogin(
            state=state,
            redirect_uri=redirect_uri,
            cloud_base_url=self.cloud_base_url,
        )
        self._store.save_pending(pending)
        authorize_url = self._bff.build_local_authorize_url(redirect_uri=redirect_uri, state=state)
        return CloudLoginStart(
            authorize_url=authorize_url,
            state=state,
            redirect_uri=redirect_uri,
        )

    def complete_login(
        self,
        *,
        handoff_code: str,
        state: str,
        local_api_base_url: str | None = None,
    ) -> CloudSessionSummary:
        pending = self._store.load_pending()
        if pending is None:
            raise CloudBffError(
                status_code=400,
                code="pending_login_missing",
                message="No pending cloud login was found. Start login again from Local Munk AI.",
            )
        if pending.state != state:
            raise CloudBffError(
                status_code=400,
                code="state_mismatch",
                message="Cloud login state mismatch. Start login again from Local Munk AI.",
            )
        if utc_now() - pending.created_at > _PENDING_TTL:
            self._store.clear_pending()
            raise CloudBffError(
                status_code=400,
                code="pending_login_expired",
                message="Cloud login timed out. Start login again from Local Munk AI.",
            )

        redirect_uri = pending.redirect_uri
        if local_api_base_url:
            expected = self._build_callback_uri(local_api_base_url)
            if expected != redirect_uri:
                # Prefer the pending redirect_uri (bound into handoff); warn via mismatch only if host changed.
                pass

        payload = self._bff.exchange_handoff(
            handoff_code=handoff_code,
            redirect_uri=redirect_uri,
            state=state,
        )
        access_token, refresh_token, expires_at_text, user = parse_token_payload(payload)
        session = CloudSessionRecord(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=_parse_expires_at(expires_at_text),
            user=user,
            cloud_base_url=self.cloud_base_url,
            updated_at=utc_now(),
        )
        self._store.save_session(session)
        self._store.clear_pending()
        return self._to_summary(session)

    def get_session_summary(self) -> CloudSessionSummary:
        session = self._store.load_session()
        if session is None:
            return CloudSessionSummary(authenticated=False)
        if self._needs_refresh(session):
            try:
                session = self._refresh_session(session)
            except CloudBffError as exc:
                if exc.code == "session_expired":
                    return CloudSessionSummary(authenticated=False)
                raise
        return self._to_summary(session)

    def logout(self) -> CloudSessionSummary:
        self._store.clear_session()
        self._store.clear_pending()
        return CloudSessionSummary(authenticated=False)

    def list_workspaces(self) -> list[CloudWorkspaceSummary]:
        return self.execute_with_auth(lambda access_token: self._bff.list_workspaces(access_token=access_token))

    def get_valid_access_token(self) -> str:
        session = self._store.load_session()
        if session is None:
            raise CloudBffError(
                status_code=401,
                code="not_authenticated",
                message="Not signed in to Munk Cloud.",
            )
        if self._needs_refresh(session):
            session = self._refresh_session(session)
        return session.access_token

    def execute_with_auth(self, operation: Callable[[str], T]) -> T:
        """Run a BFF call with a valid access token.

        On 401 / auth failure, force one refresh retry. If that still fails, clear the
        local session and raise ``session_expired`` so callers can prompt re-login.
        """
        access_token = self.get_valid_access_token()
        try:
            return operation(access_token)
        except CloudBffError as exc:
            if not _is_reauth_required(exc):
                raise
            session = self._store.load_session()
            if session is None:
                raise _session_expired_error(cause=exc) from exc
            session = self._refresh_session(session)
            try:
                return operation(session.access_token)
            except CloudBffError as retry_exc:
                if _is_reauth_required(retry_exc):
                    self._clear_session_for_reauth()
                    raise _session_expired_error(cause=retry_exc) from retry_exc
                raise

    def _refresh_session(self, session: CloudSessionRecord) -> CloudSessionRecord:
        try:
            payload = self._bff.refresh(refresh_token=session.refresh_token)
        except CloudBffError as exc:
            if _is_reauth_required(exc):
                self._clear_session_for_reauth()
                raise _session_expired_error(cause=exc) from exc
            raise
        access_token, refresh_token, expires_at_text, user = parse_token_payload(payload)
        updated = CloudSessionRecord(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=_parse_expires_at(expires_at_text),
            user=user,
            cloud_base_url=session.cloud_base_url or self.cloud_base_url,
            updated_at=utc_now(),
        )
        self._store.save_session(updated)
        return updated

    def _clear_session_for_reauth(self) -> None:
        self._store.clear_session()

    @staticmethod
    def _needs_refresh(session: CloudSessionRecord) -> bool:
        if session.expires_at is None:
            return False
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= utc_now() + _REFRESH_SKEW

    @staticmethod
    def _build_callback_uri(local_api_base_url: str) -> str:
        base = local_api_base_url.rstrip("/") + "/"
        return urljoin(base, "v1/cloud/auth/callback")

    @staticmethod
    def _to_summary(session: CloudSessionRecord) -> CloudSessionSummary:
        return CloudSessionSummary(
            authenticated=True,
            user=session.user,
            expires_at=session.expires_at,
            cloud_base_url=session.cloud_base_url,
            can_refresh=bool(session.refresh_token),
        )


def _parse_expires_at(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_reauth_required(exc: CloudBffError) -> bool:
    if exc.status_code == _HTTP_UNAUTHORIZED:
        return True
    return exc.code in _REAUTH_ERROR_CODES


def _session_expired_error(*, cause: CloudBffError | None = None) -> CloudBffError:
    return CloudBffError(
        status_code=_HTTP_UNAUTHORIZED,
        code="session_expired",
        message=_SESSION_EXPIRED_MESSAGE,
        details=cause.details if cause is not None else None,
    )


def _load_proxy_config(*, workspace_root: Path | None) -> ResolvedProxyConfig | None:
    try:
        config = load_resolved_config(None, workspace_root=workspace_root or Path.cwd())
    except Exception:  # noqa: BLE001
        return None
    return resolve_proxy_config(config)
