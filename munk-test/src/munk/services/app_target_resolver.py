from __future__ import annotations

from pathlib import Path

from munk.app import AndroidAppIdentity, AppTarget, IOSAppIdentity, WebAppIdentity
from munk.app_assets.models import normalize_app_id
from munk.app_assets.service import AppAssetService


def resolve_app_target_for_execution(
    *,
    app_id: str,
    assets_root: Path | None = None,
    app_target: AppTarget | None = None,
    platform: str | None = None,
    package: str | None = None,
    bundle_id: str | None = None,
    base_url: str | None = None,
    origin: str | None = None,
    headless: bool = False,
) -> AppTarget:
    normalized_app_id = normalize_app_id(app_id)
    if app_target is not None:
        return app_target

    explicit_platform = _explicit_platform(platform=platform, package=package, bundle_id=bundle_id, base_url=base_url)
    if explicit_platform == "android":
        if package:
            return AppTarget(
                app_id=normalized_app_id,
                platform="android",
                android=AndroidAppIdentity(package_name=package),
            )
        loaded_target = AppAssetService(root_dir=assets_root).build_app_detail(normalized_app_id).profile.to_app_target()
        if loaded_target.platform != "android" or loaded_target.android is None or not loaded_target.android.package_name.strip():
            raise ValueError("android runtime currently requires package")
        return loaded_target
    if explicit_platform == "ios":
        if not bundle_id:
            raise ValueError("ios runtime currently requires bundle_id")
        return AppTarget(
            app_id=normalized_app_id,
            platform="ios",
            ios=IOSAppIdentity(bundle_id=bundle_id),
        )
    if explicit_platform == "web":
        if not base_url:
            raise ValueError("web runtime currently requires base_url")
        return AppTarget(
            app_id=normalized_app_id,
            platform="web",
            web=WebAppIdentity(base_url=base_url, origin=origin),
            launch_context=_web_launch_context(headless=headless),
        )

    loaded_target = AppAssetService(root_dir=assets_root).build_app_detail(normalized_app_id).profile.to_app_target()
    if loaded_target.platform == "web":
        launch_context = dict(loaded_target.launch_context or {})
        launch_context.setdefault("browser", "chromium")
        launch_context.setdefault("headless", "true" if headless else "false")
        return loaded_target.model_copy(update={"launch_context": launch_context})
    return loaded_target


def _explicit_platform(
    *,
    platform: str | None,
    package: str | None,
    bundle_id: str | None,
    base_url: str | None,
) -> str | None:
    if platform is not None:
        normalized = platform.strip().lower()
        if normalized not in {"android", "ios", "web"}:
            raise ValueError(f"unsupported platform '{platform}'")
        return normalized
    if package:
        return "android"
    if bundle_id:
        return "ios"
    if base_url:
        return "web"
    return None


def _web_launch_context(*, headless: bool) -> dict[str, str]:
    return {
        "browser": "chromium",
        "headless": "true" if headless else "false",
    }
