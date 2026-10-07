from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from munk.app_assets.models import normalize_app_id
from munk.app_assets.storage import AppRegistry
from munk.config.profile_config_service import ProfileConfigService
from munk.network.proxy import ResolvedProxyConfig
from munk.paths import assets_root
from munk.services.cloud.auth_models import CloudBffError, utc_now
from munk.services.cloud.auth_service import CloudAuthService
from munk.services.cloud.bundle_hash import hash_bundle_content
from munk.services.cloud.bundle_materializer import (
    load_local_hash_inputs,
    materialize_app_sync_bundle,
)
from munk.services.cloud.link_store import CloudLinkStore
from munk.services.cloud.sync_models import (
    CloudAppSummary,
    CloudLink,
    CloudLinkSummary,
    CloudLinksView,
    CloudSyncPublishResult,
    CloudSyncPullResult,
    CloudSyncPushResult,
    CloudSyncState,
    CloudSyncStatus,
    LocalSyncConflictError,
)
from munk.services.cloud.sync_state_store import CloudSyncStateStore


class CloudSyncService:
    def __init__(
        self,
        *,
        home: Path | None = None,
        assets_root_dir: Path | None = None,
        auth_service: CloudAuthService | None = None,
        link_store: CloudLinkStore | None = None,
        sync_state_store: CloudSyncStateStore | None = None,
        config_service: ProfileConfigService | None = None,
        app_registry: AppRegistry | None = None,
        workspace_root: Path | None = None,
        proxy: ResolvedProxyConfig | None = None,
    ) -> None:
        self._home = home
        self._assets_root = assets_root_dir
        self._workspace_root = workspace_root.resolve() if workspace_root is not None else Path.cwd().resolve()
        self._auth = auth_service or CloudAuthService(
            home=home,
            workspace_root=self._workspace_root,
            proxy=proxy,
        )
        self._link_store = link_store or CloudLinkStore(home=home)
        self._sync_state_store = sync_state_store or CloudSyncStateStore(home=home)
        self._config_service = config_service or ProfileConfigService(workspace_root=self._workspace_root)
        self._app_registry = app_registry

    def list_links(self) -> CloudLinksView:
        state = self._link_store.load()
        items: list[CloudLinkSummary] = []
        for link in state.items:
            sync_state = self._sync_state_store.load(
                workspace_id=link.workspace_id,
                app_id=link.app_id,
            )
            local_hash = self._compute_local_content_hash(link.app_id)
            dirty = self._is_dirty(sync_state=sync_state, local_hash=local_hash)
            items.append(
                CloudLinkSummary(
                    workspace_id=link.workspace_id,
                    app_id=link.app_id,
                    bound_at=link.bound_at,
                    workspace_name=link.workspace_name,
                    role=link.role,
                    dirty=dirty,
                    base_revision=sync_state.base_revision if sync_state else None,
                    last_synced_at=sync_state.last_synced_at if sync_state else None,
                    last_action=sync_state.last_action if sync_state else None,
                )
            )
        return CloudLinksView(items=items, active_app_id=state.active_app_id)

    def link_app(
        self,
        *,
        workspace_id: str,
        app_id: str,
        workspace_name: str | None = None,
        role: str | None = None,
    ) -> CloudLink:
        workspace_id = workspace_id.strip()
        if not workspace_id:
            raise CloudBffError(
                status_code=400,
                code="invalid_link",
                message="workspace_id is required.",
            )
        normalized_app_id = normalize_app_id(app_id)

        status = self._auth.execute_with_auth(
            lambda access_token: self._auth.bff_client.sync_status(
                access_token=access_token,
                workspace_id=workspace_id,
                app_id=normalized_app_id,
            )
        )
        resolved_role = role or (str(status["role"]) if isinstance(status.get("role"), str) else None)

        link = CloudLink(
            workspace_id=workspace_id,
            app_id=normalized_app_id,
            bound_at=utc_now(),
            workspace_name=workspace_name,
            role=resolved_role,
        )
        self._link_store.upsert_link(link, make_active=True)
        return link

    def unlink_app(self, *, app_id: str) -> CloudLinksView:
        normalized_app_id = normalize_app_id(app_id)
        _state, removed = self._link_store.remove_link(normalized_app_id)
        if removed is not None:
            self._sync_state_store.clear(
                workspace_id=removed.workspace_id,
                app_id=removed.app_id,
            )
        return self.list_links()

    def set_active_app(self, *, app_id: str) -> CloudLinksView:
        normalized_app_id = normalize_app_id(app_id)
        try:
            self._link_store.set_active(normalized_app_id)
        except KeyError as err:
            raise CloudBffError(
                status_code=404,
                code="link_not_found",
                message=f"Linked app '{normalized_app_id}' was not found.",
            ) from err
        return self.list_links()

    def list_apps(self, *, workspace_id: str) -> list[CloudAppSummary]:
        workspace_id = workspace_id.strip()
        return self._auth.execute_with_auth(
            lambda access_token: self._auth.bff_client.list_apps(
                access_token=access_token,
                workspace_id=workspace_id,
            )
        )

    def get_status(self, *, app_id: str | None = None) -> CloudSyncStatus:
        link = self._require_link(app_id=app_id)
        cloud = self._auth.execute_with_auth(
            lambda access_token: self._auth.bff_client.sync_status(
                access_token=access_token,
                workspace_id=link.workspace_id,
                app_id=link.app_id,
            )
        )
        sync_state = self._sync_state_for_link(link)
        local_hash = self._compute_local_content_hash(link.app_id)
        dirty = self._is_dirty(sync_state=sync_state, local_hash=local_hash)

        return CloudSyncStatus(
            workspace_id=link.workspace_id,
            app_id=link.app_id,
            revision=int(cloud.get("revision") or 0),
            content_hash=cloud.get("content_hash") if isinstance(cloud.get("content_hash"), str) else None,
            role=str(cloud.get("role") or link.role or "member"),
            can_pull=bool(cloud.get("can_pull", True)),
            can_push=bool(cloud.get("can_push", False)),
            can_force_push=bool(cloud.get("can_force_push", False)),
            base_revision=sync_state.base_revision if sync_state else None,
            local_content_hash=local_hash,
            dirty=dirty,
            last_synced_at=sync_state.last_synced_at if sync_state else None,
            last_action=sync_state.last_action if sync_state else None,
            bound=True,
        )

    def pull(self, *, force: bool = False, app_id: str | None = None) -> CloudSyncPullResult:
        link = self._require_link(app_id=app_id)
        cloud_status = self._auth.execute_with_auth(
            lambda access_token: self._auth.bff_client.sync_status(
                access_token=access_token,
                workspace_id=link.workspace_id,
                app_id=link.app_id,
            )
        )
        cloud_revision = int(cloud_status.get("revision") or 0)
        cloud_hash = (
            cloud_status.get("content_hash")
            if isinstance(cloud_status.get("content_hash"), str)
            else None
        )

        sync_state = self._sync_state_for_link(link)
        local_hash = self._compute_local_content_hash(link.app_id)
        dirty = self._is_dirty(sync_state=sync_state, local_hash=local_hash)

        if (
            not force
            and sync_state is not None
            and dirty
            and cloud_revision > sync_state.base_revision
        ):
            raise LocalSyncConflictError(
                message=(
                    "Local assets changed since the last sync and the cloud revision advanced. "
                    "Pull with force=true to discard local changes, or push from an admin host."
                ),
                base_revision=sync_state.base_revision,
                cloud_revision=cloud_revision,
                local_content_hash=local_hash,
                cloud_content_hash=cloud_hash,
            )

        bundle = self._auth.execute_with_auth(
            lambda access_token: self._auth.bff_client.sync_pull(
                access_token=access_token,
                workspace_id=link.workspace_id,
                app_id=link.app_id,
            )
        )
        result = materialize_app_sync_bundle(
            bundle,
            assets_root=self._resolve_assets_root(),
            config_service=self._config_service,
        )

        local_after = self._compute_local_content_hash(link.app_id)
        new_state = CloudSyncState(
            workspace_id=link.workspace_id,
            app_id=link.app_id,
            base_revision=bundle.revision,
            content_hash=local_after,
            dirty=False,
            last_synced_at=utc_now(),
            last_action="pull",
        )
        self._sync_state_store.save(new_state)

        return CloudSyncPullResult(
            workspace_id=link.workspace_id,
            app_id=link.app_id,
            revision=bundle.revision,
            content_hash=local_after,
            dirty=False,
            forced=force,
            plans_written=result.plans_written,
            plans_deleted=result.plans_deleted,
        )

    def push(self, *, force: bool = False, app_id: str | None = None) -> CloudSyncPushResult:
        link = self._require_link(app_id=app_id)
        cloud_status = self._auth.execute_with_auth(
            lambda access_token: self._auth.bff_client.sync_status(
                access_token=access_token,
                workspace_id=link.workspace_id,
                app_id=link.app_id,
            )
        )

        can_push = bool(cloud_status.get("can_push", False))
        can_force_push = bool(cloud_status.get("can_force_push", False))
        if force:
            if not can_force_push:
                raise CloudBffError(
                    status_code=403,
                    code="forbidden_not_admin",
                    message="Only workspace owner/admin can force-push.",
                )
        elif not can_push:
            raise CloudBffError(
                status_code=403,
                code="forbidden_not_admin",
                message="Only workspace owner/admin can push.",
            )

        inputs = load_local_hash_inputs(
            app_id=link.app_id,
            assets_root=self._resolve_assets_root(),
            config_service=self._config_service,
        )
        if inputs is None:
            raise CloudBffError(
                status_code=422,
                code="local_app_missing",
                message=f"Local app '{link.app_id}' was not found under assets.",
            )

        content_hash = hash_bundle_content(**inputs)
        sync_state = self._sync_state_for_link(link)
        if sync_state is not None:
            expected_revision = sync_state.base_revision
        else:
            expected_revision = int(cloud_status.get("revision") or 0)

        def _write(access_token: str) -> CloudSyncPushResult:
            write_common = {
                "access_token": access_token,
                "workspace_id": link.workspace_id,
                "app_id": link.app_id,
                "expected_revision": expected_revision,
                "app_profile": inputs["app_profile"],
                "plans": inputs["plans"],
                "content_hash": content_hash,
                "introduction": inputs.get("introduction"),
                "knowledge_document": inputs.get("knowledge_document"),
                "team_config": inputs.get("team_config") or {},
            }
            if force:
                return self._auth.bff_client.sync_force_push(**write_common)
            return self._auth.bff_client.sync_push(**write_common)

        remote = self._auth.execute_with_auth(_write)
        action: Literal["push", "force_push"] = "force_push" if force else "push"
        if remote.action in ("push", "force_push"):
            action = remote.action

        local_after = self._compute_local_content_hash(link.app_id)
        new_state = CloudSyncState(
            workspace_id=link.workspace_id,
            app_id=link.app_id,
            base_revision=remote.revision,
            content_hash=local_after,
            dirty=False,
            last_synced_at=utc_now(),
            last_action=action,
        )
        self._sync_state_store.save(new_state)

        return CloudSyncPushResult(
            workspace_id=link.workspace_id,
            app_id=link.app_id,
            revision=remote.revision,
            content_hash=local_after,
            action=action,
            forced=force,
        )

    def publish(
        self,
        *,
        workspace_id: str,
        app_id: str,
        workspace_name: str | None = None,
    ) -> CloudSyncPublishResult:
        """Ensure cloud app shell exists, link it, then push local assets."""
        workspace_id = workspace_id.strip()
        if not workspace_id:
            raise CloudBffError(
                status_code=400,
                code="invalid_publish",
                message="workspace_id is required.",
            )
        normalized_app_id = normalize_app_id(app_id)

        try:
            profile = self._resolve_app_registry().load(normalized_app_id)
        except FileNotFoundError as err:
            raise CloudBffError(
                status_code=422,
                code="local_app_missing",
                message=f"Local app '{normalized_app_id}' was not found under assets.",
            ) from err

        android_payload: dict[str, Any] | None = None
        ios_payload: dict[str, Any] | None = None
        web_payload: dict[str, Any] | None = None
        if profile.platform == "android" and profile.android is not None:
            android_payload = {"package_name": profile.android.package_name}
        elif profile.platform == "ios" and profile.ios is not None:
            ios_payload = {"bundle_id": profile.ios.bundle_id}
        elif profile.platform == "web" and profile.web is not None:
            web_payload = {"base_url": profile.web.base_url or ""}
            if profile.web.origin:
                web_payload["origin"] = profile.web.origin

        ensured = self._auth.execute_with_auth(
            lambda access_token: self._auth.bff_client.ensure_app(
                access_token=access_token,
                workspace_id=workspace_id,
                app_id=profile.app_id,
                platform=profile.platform,
                app_name=profile.app_name,
                app_introduction_ref=profile.app_introduction_ref,
                app_knowledge_ref=profile.app_knowledge_ref,
                android=android_payload,
                ios=ios_payload,
                web=web_payload,
            )
        )
        if not ensured.can_push:
            raise CloudBffError(
                status_code=403,
                code="forbidden_not_admin",
                message="Only workspace owner/admin can publish.",
            )
        if ensured.revision > 0:
            raise CloudBffError(
                status_code=409,
                code="cloud_app_already_published",
                message=(
                    f"Cloud app '{ensured.app_id}' already has revision {ensured.revision}. "
                    "Link it and use Push / Force Push instead of Publish."
                ),
                details={
                    "workspace_id": ensured.workspace_id,
                    "app_id": ensured.app_id,
                    "revision": ensured.revision,
                },
            )

        self.link_app(
            workspace_id=workspace_id,
            app_id=normalized_app_id,
            workspace_name=workspace_name,
            role=ensured.role,
        )
        push_result = self.push(force=False, app_id=normalized_app_id)
        return CloudSyncPublishResult(
            workspace_id=push_result.workspace_id,
            app_id=push_result.app_id,
            revision=push_result.revision,
            content_hash=push_result.content_hash,
            action=push_result.action,
            forced=push_result.forced,
            shell_created=ensured.created,
        )

    def _require_link(self, *, app_id: str | None = None) -> CloudLink:
        if app_id is not None and app_id.strip():
            normalized = normalize_app_id(app_id)
            state = self._link_store.load()
            for item in state.items:
                if item.app_id == normalized:
                    return item
            raise CloudBffError(
                status_code=404,
                code="link_not_found",
                message=f"Linked app '{normalized}' was not found.",
            )
        link = self._link_store.get_active()
        if link is None:
            raise CloudBffError(
                status_code=400,
                code="not_bound",
                message="No active linked app. Link a sync target before syncing.",
            )
        return link

    def _sync_state_for_link(self, link: CloudLink) -> CloudSyncState | None:
        return self._sync_state_store.load(
            workspace_id=link.workspace_id,
            app_id=link.app_id,
        )

    def _resolve_assets_root(self) -> Path:
        if self._assets_root is not None:
            return self._assets_root.resolve()
        return assets_root().resolve()

    def _resolve_app_registry(self) -> AppRegistry:
        if self._app_registry is not None:
            return self._app_registry
        return AppRegistry(root_dir=self._resolve_assets_root())

    def _compute_local_content_hash(self, app_id: str) -> str | None:
        inputs = load_local_hash_inputs(
            app_id=app_id,
            assets_root=self._resolve_assets_root(),
            config_service=self._config_service,
        )
        if inputs is None:
            return None
        return hash_bundle_content(**inputs)

    @staticmethod
    def _is_dirty(*, sync_state: CloudSyncState | None, local_hash: str | None) -> bool:
        if sync_state is None or sync_state.content_hash is None:
            return False
        if local_hash is None:
            return True
        return local_hash != sync_state.content_hash
