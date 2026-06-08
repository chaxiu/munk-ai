from __future__ import annotations

from typing import cast

from munk.adapters.shared.payload_models import AppDetailData, AppListData, AppListItemData
from munk.app import AppPlatform
from munk.app_assets.service import AppAssetService
from munk.app_assets.storage import AppRegistry


def list_apps_payload(*, service: AppAssetService, platform: str | None = None) -> AppListData:
    normalized_platform = coerce_platform(platform) if platform is not None else None
    items = []
    for profile in service.list_profiles(platform=normalized_platform):
        usage = service.get_app_usage(profile.app_id)
        items.append(
            AppListItemData(
                app_id=profile.app_id,
                app_name=profile.app_name,
                platform=profile.platform,
                entry_identity=profile.entry_identity,
                introduction_exists=service.app_registry.introduction_path(
                    profile.app_id,
                    ref=profile.app_introduction_ref,
                ).exists(),
                plan_count=usage.plan_count,
                case_count=usage.case_count,
            )
        )
    return AppListData(items=items)


def get_app_detail_payload(*, service: AppAssetService, app_id: str) -> AppDetailData:
    detail = service.build_app_detail(AppRegistry.normalize_app_id(app_id))
    return AppDetailData(
        profile=detail.profile,
        introduction_markdown=detail.introduction_markdown,
        app_knowledge_content=detail.app_knowledge_content,
        app_knowledge_exists=detail.app_knowledge_exists,
        app_target=detail.profile.to_app_target(),
        plan_count=detail.usage.plan_count,
        case_count=detail.usage.case_count,
    )


def coerce_platform(platform: str) -> AppPlatform:
    if platform in {"android", "ios", "web"}:
        return cast(AppPlatform, platform)
    raise ValueError(f"unsupported platform '{platform}'")
