from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageSpec:
    name: str
    default_relpath: str
    config_section: str | None = None
    config_key: str | None = None
    layer: str = "core"


@dataclass(frozen=True)
class RuntimeLayerSpec:
    provider: str | None = None
    runtime: str | None = None
    resource_mode: str | None = None
    owned_resource_templates: tuple[str, ...] = ()
    owned_data_relpaths: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    package_specs: tuple[PackageSpec, ...]
    enabled_by_default: bool = False
    runtime_name: str | None = None
    install_mode: str = "editable"
    provider_name: str | None = None
    layer_spec: RuntimeLayerSpec | None = None


CORE_PACKAGE_SPECS: tuple[PackageSpec, ...] = (
    PackageSpec(
        name="munk-device-api",
        default_relpath="packages/devices/device-api",
    ),
    PackageSpec(
        name="munk-device-android-runtime",
        default_relpath="packages/devices/device-runtime-android",
        config_section="device",
        config_key="android_runtime_path",
    ),
    PackageSpec(
        name="munk-device-ios-runtime",
        default_relpath="packages/devices/device-runtime-ios",
        config_section="device",
        config_key="ios_runtime_path",
    ),
    PackageSpec(
        name="munk-device-web-runtime",
        default_relpath="packages/devices/device-runtime-web",
        config_section="device",
        config_key="web_runtime_path",
    ),
    PackageSpec(
        name="munk-shared-api",
        default_relpath="packages/shared/shared-api",
    ),
    PackageSpec(
        name="munk-shared-tools-api",
        default_relpath="packages/shared/shared-tools-api",
    ),
    PackageSpec(
        name="munk-agent-base",
        default_relpath="packages/shared/agent-base",
    ),
    PackageSpec(
        name="munk-perception-api",
        default_relpath="packages/shared/perception-api",
        config_section="perception",
        config_key="api_path",
    ),
    PackageSpec(
        name="munk-plan-agent-api",
        default_relpath="packages/agents/plan-agent-api",
        config_section="plan",
        config_key="api_path",
    ),
    PackageSpec(
        name="munk-review-agent-api",
        default_relpath="packages/agents/review-agent-api",
        config_section="review",
        config_key="api_path",
    ),
    PackageSpec(
        name="munk-judge-agent-api",
        default_relpath="packages/agents/judge-agent-api",
        config_section="judge",
        config_key="api_path",
    ),
    PackageSpec(
        name="munk-optimize-agent-api",
        default_relpath="packages/agents/optimize-agent-api",
        config_section="optimize",
        config_key="api_path",
    ),
    PackageSpec(
        name="munk-runner-agent-api",
        default_relpath="packages/agents/runner-agent-api",
        config_section="runner",
        config_key="api_path",
    ),
)


FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        name="perception",
        enabled_by_default=True,
        install_mode="editable",
        provider_name="full",
        package_specs=(
            PackageSpec(
                name="munk-perception-full-sdk",
                default_relpath="packages/shared/perception-sdk-full",
                config_section="perception",
                config_key="provider_path",
                layer="perception",
            ),
        ),
        layer_spec=RuntimeLayerSpec(
            provider="full",
            resource_mode="package_data",
            owned_resource_templates=("{site_packages_relpath}/munk_perception_full/resources",),
        ),
    ),
    FeatureSpec(
        name="plan",
        runtime_name="local",
        install_mode="editable",
        package_specs=(
            PackageSpec(
                name="munk-plan-agent-runtime-local",
                default_relpath="packages/agents/plan-agent-runtime-local",
                config_section="plan",
                config_key="runtime_path",
                layer="plan",
            ),
        ),
        layer_spec=RuntimeLayerSpec(runtime="local", owned_data_relpaths=("data/plan-runtime-local",)),
    ),
    FeatureSpec(
        name="runner",
        runtime_name="local",
        install_mode="editable",
        package_specs=(
            PackageSpec(
                name="munk-runner-agent-runtime-local",
                default_relpath="packages/agents/runner-agent-runtime-local",
                config_section="runner",
                config_key="runtime_path",
                layer="runner",
            ),
        ),
        layer_spec=RuntimeLayerSpec(runtime="local"),
    ),
    FeatureSpec(
        name="knowledge",
        runtime_name="local",
        install_mode="editable",
        package_specs=(
            PackageSpec(
                name="munk-knowledge-api",
                default_relpath="packages/shared/knowledge-api",
                config_section="knowledge",
                config_key="shared_api_path",
                layer="knowledge",
            ),
            PackageSpec(
                name="munk-knowledge-runtime-local",
                default_relpath="packages/shared/knowledge-runtime-local",
                config_section="knowledge",
                config_key="shared_runtime_path",
                layer="knowledge",
            ),
            PackageSpec(
                name="munk-knowledge-agent-api",
                default_relpath="packages/agents/knowledge-agent-api",
                config_section="knowledge",
                config_key="api_path",
                layer="knowledge",
            ),
            PackageSpec(
                name="munk-knowledge-agent-runtime-local",
                default_relpath="packages/agents/knowledge-agent-runtime-local",
                config_section="knowledge",
                config_key="runtime_path",
                layer="knowledge",
            ),
        ),
        layer_spec=RuntimeLayerSpec(runtime="local"),
    ),
    FeatureSpec(
        name="review",
        runtime_name="local",
        install_mode="editable",
        package_specs=(
            PackageSpec(
                name="munk-review-agent-runtime-local",
                default_relpath="packages/agents/review-agent-runtime-local",
                config_section="review",
                config_key="runtime_path",
                layer="review",
            ),
        ),
        layer_spec=RuntimeLayerSpec(
            runtime="local",
            resource_mode="package_data",
            owned_resource_templates=("{site_packages_relpath}/munk_review_local/resources",),
            owned_data_relpaths=("data/review-runtime-local",),
        ),
    ),
    FeatureSpec(
        name="judge",
        runtime_name="local",
        install_mode="editable",
        package_specs=(
            PackageSpec(
                name="munk-judge-agent-runtime-local",
                default_relpath="packages/agents/judge-agent-runtime-local",
                config_section="judge",
                config_key="runtime_path",
                layer="judge",
            ),
        ),
        layer_spec=RuntimeLayerSpec(runtime="local", owned_data_relpaths=("data/judge-runtime-local",)),
    ),
    FeatureSpec(
        name="optimize",
        runtime_name="local",
        install_mode="editable",
        package_specs=(
            PackageSpec(
                name="munk-optimize-agent-runtime-local",
                default_relpath="packages/agents/optimize-agent-runtime-local",
                config_section="optimize",
                config_key="runtime_path",
                layer="optimize",
            ),
        ),
        layer_spec=RuntimeLayerSpec(runtime="local", owned_data_relpaths=("data/optimize-runtime-local",)),
    ),
    FeatureSpec(
        name="recording",
        runtime_name="local",
        install_mode="editable",
        package_specs=(
            PackageSpec(
                name="munk-recording-agent-api",
                default_relpath="packages/agents/recording-agent-api",
                config_section="recording",
                config_key="api_path",
                layer="core",
            ),
            PackageSpec(
                name="munk-recording-agent-runtime-local",
                default_relpath="packages/agents/recording-agent-runtime-local",
                config_section="recording",
                config_key="runtime_path",
                layer="recording",
            ),
        ),
        layer_spec=RuntimeLayerSpec(runtime="local"),
    ),
)


FEATURE_ORDER: tuple[str, ...] = tuple(feature.name for feature in FEATURE_SPECS)
FEATURE_SPECS_BY_NAME: dict[str, FeatureSpec] = {feature.name: feature for feature in FEATURE_SPECS}


def iter_feature_specs() -> tuple[FeatureSpec, ...]:
    return FEATURE_SPECS


def feature_is_enabled(raw: dict[str, dict[str, str]], *, feature_name: str) -> bool:
    feature = FEATURE_SPECS_BY_NAME[feature_name]
    return feature.enabled_by_default or feature_name in raw


def build_distribution_layer_map() -> dict[str, str]:
    mapping = {"munk": "core"}
    for package in CORE_PACKAGE_SPECS:
        mapping[package.name] = package.layer
    for feature in FEATURE_SPECS:
        for package in feature.package_specs:
            mapping[package.name] = package.layer
    return mapping


def build_runtime_layer_specs() -> dict[str, RuntimeLayerSpec]:
    specs: dict[str, RuntimeLayerSpec] = {}
    for feature in FEATURE_SPECS:
        if feature.layer_spec is None:
            continue
        layer_name = _feature_runtime_layer_name(feature)
        if layer_name is None:
            continue
        specs[layer_name] = feature.layer_spec
    return specs


def build_runtime_data_dir_relpaths(raw: dict[str, dict[str, str]] | None = None) -> list[str]:
    relpaths = ["data/runs", "data/operations"]
    for feature in FEATURE_SPECS:
        if raw is not None and not feature_is_enabled(raw, feature_name=feature.name):
            continue
        if feature.layer_spec is None:
            continue
        relpaths.extend(feature.layer_spec.owned_data_relpaths)
    return list(dict.fromkeys(relpaths))


def _feature_runtime_layer_name(feature: FeatureSpec) -> str | None:
    for package in feature.package_specs:
        if package.layer != "core":
            return package.layer
    return None
