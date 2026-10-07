from __future__ import annotations

import pytest
from munk.app import AndroidAppIdentity, AppTarget, IOSAppIdentity, WebAppIdentity


def test_app_target_derives_android_entry_identity() -> None:
    target = AppTarget(
        app_id="demo-app",
        platform="android",
        android=AndroidAppIdentity(package_name="com.demo.app", activity_name=".MainActivity"),
    )

    assert target.entry_identity == "com.demo.app"


def test_app_target_derives_web_entry_identity() -> None:
    target = AppTarget(
        app_id="demo-web",
        platform="web",
        web=WebAppIdentity(base_url="https://example.com", origin="https://example.com"),
    )

    assert target.entry_identity == "https://example.com"


def test_app_target_accepts_matching_explicit_entry_identity() -> None:
    target = AppTarget(
        app_id="demo-app",
        platform="android",
        entry_identity="com.demo.app",
        android=AndroidAppIdentity(package_name="com.demo.app"),
    )

    assert target.entry_identity == "com.demo.app"


@pytest.mark.parametrize(
    ("target_kwargs", "expected_entry_identity"),
    [
        (
            {
                "app_id": "demo-android",
                "platform": "android",
                "entry_identity": "wrong.android",
                "android": AndroidAppIdentity(package_name="com.demo.app"),
            },
            "com.demo.app",
        ),
        (
            {
                "app_id": "demo-ios",
                "platform": "ios",
                "entry_identity": "wrong.ios",
                "ios": IOSAppIdentity(bundle_id="dev.demo.app"),
            },
            "dev.demo.app",
        ),
        (
            {
                "app_id": "demo-web",
                "platform": "web",
                "entry_identity": "https://wrong.example.com",
                "web": WebAppIdentity(origin="https://example.com"),
            },
            "https://example.com",
        ),
    ],
)
def test_app_target_rejects_mismatched_entry_identity(
    target_kwargs: dict[str, object],
    expected_entry_identity: str,
) -> None:
    with pytest.raises(ValueError, match="entry_identity must match"):
        AppTarget(**target_kwargs)


def test_app_target_rejects_mismatched_platform_identity() -> None:
    with pytest.raises(ValueError):
        AppTarget(
            app_id="demo-ios",
            platform="ios",
            android=AndroidAppIdentity(package_name="com.demo.app"),
            ios=IOSAppIdentity(bundle_id="dev.demo.app"),
        )
