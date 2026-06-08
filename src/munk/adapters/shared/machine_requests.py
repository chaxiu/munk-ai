from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, BaseModel, Field

from munk.app import AndroidAppIdentity, AppTarget, IOSAppIdentity, WebAppIdentity
from munk.execution.models import ChangeVerificationRequest, PlanExecutionRequest, RuntimeOverrideValue
from munk.planning.models import RequirementInput
from munk.reviewing.models import ReviewRequest
from munk.services.app_target_resolver import resolve_app_target_for_execution


def empty_runtime_overrides() -> dict[str, RuntimeOverrideValue]:
    return {}


class PlanCliRequest(BaseModel):
    app_id: str
    requirement_doc_path: Path
    technical_doc_path: Path | None = None
    user_prompt: str | None = None
    artifact_path: Path | None = None
    assets_root: Path | None = None
    artifact_url: str | None = None
    auto_run: bool = False
    device_ref: str | None = Field(default=None, validation_alias=AliasChoices("device_ref", "serial"))
    package: str | None = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=empty_runtime_overrides)

    def to_requirement_input(self) -> RequirementInput:
        return RequirementInput(
            app_id=self.app_id,
            requirement_doc_path=self.requirement_doc_path,
            technical_doc_path=self.technical_doc_path,
            user_prompt=self.user_prompt,
            artifact_path=self.artifact_path,
            assets_root=self.assets_root,
            artifact_url=self.artifact_url,
            auto_run=self.auto_run,
        )

    def to_plan_execution_request(self) -> PlanExecutionRequest:
        return PlanExecutionRequest(
            app_id=self.app_id,
            plan_id="",
            app_target=_build_android_app_target(app_id=self.app_id, package=self.package),
            device_ref=self.device_ref,
            artifact_path=self.artifact_path,
            assets_root=self.assets_root,
            runtime_overrides=dict(self.runtime_overrides),
        )


class RunCaseCliRequest(BaseModel):
    app_id: str
    plan_id: str
    case_id: str
    app_target: AppTarget | None = None
    device_ref: str | None = Field(default=None, validation_alias=AliasChoices("device_ref", "serial"))
    package: str | None = None
    artifact_path: Path | None = None
    assets_root: Path | None = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=empty_runtime_overrides)

    def to_plan_execution_request(self) -> PlanExecutionRequest:
        return PlanExecutionRequest(
            app_id=self.app_id,
            plan_id=self.plan_id,
            app_target=self.app_target or _build_android_app_target(app_id=self.app_id, package=self.package),
            device_ref=self.device_ref,
            artifact_path=self.artifact_path,
            assets_root=self.assets_root,
            runtime_overrides=dict(self.runtime_overrides),
        )


class RunPlanCliRequest(BaseModel):
    app_id: str
    plan_id: str
    app_target: AppTarget | None = None
    device_ref: str | None = Field(default=None, validation_alias=AliasChoices("device_ref", "serial"))
    package: str | None = None
    bundle_id: str | None = None
    base_url: str | None = None
    origin: str | None = None
    headless: bool = False
    artifact_path: Path | None = None
    assets_root: Path | None = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=empty_runtime_overrides)
    fail_fast: bool = False

    def to_plan_execution_request(self) -> PlanExecutionRequest:
        return PlanExecutionRequest(
            app_id=self.app_id,
            plan_id=self.plan_id,
            app_target=resolve_app_target_for_execution(
                app_id=self.app_id,
                assets_root=self.assets_root,
                app_target=self.app_target,
                package=self.package,
                bundle_id=self.bundle_id,
                base_url=self.base_url,
                origin=self.origin,
                headless=self.headless,
            ),
            device_ref=self.device_ref,
            artifact_path=self.artifact_path,
            assets_root=self.assets_root,
            runtime_overrides=dict(self.runtime_overrides),
            fail_fast=self.fail_fast,
        )


class RunPlansCliRequest(BaseModel):
    app_id: str
    plan_ids: list[str]
    app_target: AppTarget | None = None
    device_ref: str | None = Field(default=None, validation_alias=AliasChoices("device_ref", "serial"))
    package: str | None = None
    bundle_id: str | None = None
    base_url: str | None = None
    origin: str | None = None
    headless: bool = False
    artifact_path: Path | None = None
    assets_root: Path | None = None
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(default_factory=empty_runtime_overrides)
    fail_fast: bool = False

    def to_plan_execution_request(self, *, plan_id: str) -> PlanExecutionRequest:
        return PlanExecutionRequest(
            app_id=self.app_id,
            plan_id=plan_id,
            app_target=resolve_app_target_for_execution(
                app_id=self.app_id,
                assets_root=self.assets_root,
                app_target=self.app_target,
                package=self.package,
                bundle_id=self.bundle_id,
                base_url=self.base_url,
                origin=self.origin,
                headless=self.headless,
            ),
            device_ref=self.device_ref,
            artifact_path=self.artifact_path,
            assets_root=self.assets_root,
            runtime_overrides=dict(self.runtime_overrides),
            fail_fast=self.fail_fast,
        )


class VerifyChangeCliRequest(ChangeVerificationRequest):
    pass


class ReviewCliRequest(ReviewRequest):
    pass


class AppLifecycleRequest(BaseModel):
    app_id: str
    app_target: AppTarget | None = None
    device_ref: str | None = Field(default=None, validation_alias=AliasChoices("device_ref", "serial"))
    assets_root: Path | None = None
    platform: str | None = None
    package: str | None = None
    bundle_id: str | None = None
    base_url: str | None = None
    origin: str | None = None
    headless: bool = False

    def to_app_target(self) -> AppTarget:
        return resolve_app_target_for_execution(
            app_id=self.app_id,
            assets_root=self.assets_root,
            app_target=self.app_target,
            platform=self.platform,
            package=self.package,
            bundle_id=self.bundle_id,
            base_url=self.base_url,
            origin=self.origin,
            headless=self.headless,
        )


class AppLaunchRequest(AppLifecycleRequest):
    pass


class AppStopRequest(AppLifecycleRequest):
    pass


class AppInstallRequest(AppLifecycleRequest):
    artifact_path: Path


def _build_android_app_target(*, app_id: str, package: str | None) -> AppTarget:
    if not package:
        raise ValueError("android runtime currently requires package")
    return AppTarget(
        app_id=app_id,
        platform="android",
        android=AndroidAppIdentity(package_name=package),
    )


def build_web_app_target(
    *,
    app_id: str,
    base_url: str | None,
    origin: str | None = None,
    headless: bool = False,
) -> AppTarget:
    if not base_url:
        raise ValueError("web runtime currently requires base_url")
    return AppTarget(
        app_id=app_id,
        platform="web",
        web=WebAppIdentity(base_url=base_url, origin=origin),
        launch_context={
            "browser": "chromium",
            "headless": "true" if headless else "false",
        },
    )


def build_ios_app_target(
    *,
    app_id: str,
    bundle_id: str | None,
) -> AppTarget:
    if not bundle_id:
        raise ValueError("ios runtime currently requires bundle_id")
    return AppTarget(
        app_id=app_id,
        platform="ios",
        ios=IOSAppIdentity(bundle_id=bundle_id),
    )
