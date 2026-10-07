from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from munk.app_assets.models import AppProfile
from munk.app_assets.storage import AppRegistry
from munk.app_knowledge import build_app_knowledge_index
from munk.config.profile_config_service import ProfileConfigService
from munk.planning.models import RequirementPlan
from munk.planning.storage import PlanStore
from munk.services.cloud.sync_models import AppSyncBundle
from munk.services.knowledge import validate_app_knowledge_document


@dataclass(frozen=True)
class MaterializeResult:
    plans_written: int
    plans_deleted: int
    app_id: str


def strip_plan_payload(raw: dict[str, Any], *, app_id: str) -> dict[str, Any]:
    """Drop cloud-only fields (metadata / case ordinal) before RequirementPlan validate."""
    cases_raw = raw.get("cases")
    cases: list[dict[str, Any]] = []
    if isinstance(cases_raw, list):
        for item in cases_raw:
            if not isinstance(item, dict):
                continue
            case = dict(item)
            case.pop("metadata", None)
            case.pop("ordinal", None)
            cases.append(case)
    return {
        "plan_id": raw.get("plan_id"),
        "name": raw.get("name"),
        "app_id": raw.get("app_id") or app_id,
        "source": raw.get("source"),
        "version": raw.get("version"),
        "acceptance_criteria": raw.get("acceptance_criteria") or [],
        "cases": cases,
        "source_metadata": raw.get("source_metadata") or {},
    }


def _materialize_profile_and_intro(bundle: AppSyncBundle, registry: AppRegistry) -> AppProfile:
    profile = AppProfile.model_validate(bundle.app_profile)
    if profile.app_id != bundle.app_id:
        raise ValueError(
            f"Bundle app_id {bundle.app_id!r} does not match app_profile.app_id {profile.app_id!r}"
        )
    registry.save(profile)
    introduction = bundle.introduction if bundle.introduction is not None else ""
    registry.save_introduction(
        profile.app_id,
        introduction,
        ref=profile.app_introduction_ref,
    )
    return profile


def _materialize_knowledge(
    bundle: AppSyncBundle,
    *,
    profile: AppProfile,
    registry: AppRegistry,
    rebuild_knowledge_index: bool,
) -> None:
    knowledge_path = registry.knowledge_path(profile.app_id, ref=profile.app_knowledge_ref)
    if bundle.knowledge_document is None:
        if knowledge_path.exists():
            knowledge_path.unlink()
        return

    knowledge_text = json.dumps(bundle.knowledge_document, ensure_ascii=False, indent=2)
    validate_app_knowledge_document(knowledge_text, expected_app_id=profile.app_id)
    registry.save_knowledge(
        profile.app_id,
        knowledge_text,
        ref=profile.app_knowledge_ref,
    )
    if rebuild_knowledge_index:
        build_app_knowledge_index(
            app_id=profile.app_id,
            assets_root=registry.root_dir,
            ref=profile.app_knowledge_ref,
        )


def _materialize_plans(
    bundle: AppSyncBundle,
    *,
    profile: AppProfile,
    plan_store: PlanStore,
) -> tuple[int, int]:
    cloud_plan_ids: set[str] = set()
    plans_written = 0
    for raw_plan in bundle.plans:
        if not isinstance(raw_plan, dict):
            raise ValueError("Each plan in AppSyncBundle.plans must be an object")
        plan = RequirementPlan.model_validate(strip_plan_payload(raw_plan, app_id=profile.app_id))
        if plan.app_id != profile.app_id:
            raise ValueError(
                f"Plan {plan.plan_id!r} app_id {plan.app_id!r} does not match bundle app {profile.app_id!r}"
            )
        cloud_plan_ids.add(plan.plan_id)
        existing = plan_store.plans_dir / plan.app_id / f"{plan.plan_id}.json"
        if existing.exists():
            plan_store.replace(plan)
        else:
            plan_store.save(plan)
        plans_written += 1

    plans_deleted = 0
    for local_plan_id in plan_store.list_plan_ids(profile.app_id):
        if local_plan_id not in cloud_plan_ids:
            plan_store.delete(profile.app_id, local_plan_id)
            plans_deleted += 1
    return plans_written, plans_deleted


def materialize_app_sync_bundle(
    bundle: AppSyncBundle,
    *,
    assets_root: Path,
    config_service: ProfileConfigService,
    rebuild_knowledge_index: bool = True,
) -> MaterializeResult:
    registry = AppRegistry(root_dir=assets_root)
    plan_store = PlanStore(root_dir=assets_root)

    profile = _materialize_profile_and_intro(bundle, registry)
    _materialize_knowledge(
        bundle,
        profile=profile,
        registry=registry,
        rebuild_knowledge_index=rebuild_knowledge_index,
    )
    plans_written, plans_deleted = _materialize_plans(
        bundle,
        profile=profile,
        plan_store=plan_store,
    )

    team_config = bundle.team_config if isinstance(bundle.team_config, dict) else {}
    config_service.apply_shared_config(team_config)

    return MaterializeResult(
        plans_written=plans_written,
        plans_deleted=plans_deleted,
        app_id=profile.app_id,
    )


def load_local_hash_inputs(
    *,
    app_id: str,
    assets_root: Path,
    config_service: ProfileConfigService,
) -> dict[str, Any] | None:
    """Assemble local assets into hash_bundle_content kwargs. None if app missing."""
    registry = AppRegistry(root_dir=assets_root)
    if not registry.exists(app_id):
        return None

    profile = registry.load(app_id)
    profile_dict = profile.model_dump(mode="json", exclude_none=True)
    # Align with BFF hash bags even though local AppProfile does not persist them.
    profile_dict.setdefault("config", {})
    profile_dict.setdefault("metadata", {})

    try:
        introduction = registry.load_introduction(app_id, ref=profile.app_introduction_ref)
    except FileNotFoundError:
        introduction = None

    knowledge_document: dict[str, Any] | None = None
    try:
        raw = registry.load_knowledge(app_id, ref=profile.app_knowledge_ref)
    except FileNotFoundError:
        raw = ""
    if raw.strip():
        knowledge_document = json.loads(raw)

    plan_store = PlanStore(root_dir=assets_root)
    plans: list[dict[str, Any]] = []
    for plan_id in plan_store.list_plan_ids(app_id):
        plan = plan_store.load(app_id, plan_id)
        plans.append(plan.model_dump(mode="json"))

    return {
        "app_id": app_id,
        "app_profile": profile_dict,
        "introduction": introduction,
        "knowledge_document": knowledge_document,
        "plans": plans,
        "team_config": config_service.export_shared_config(),
    }
