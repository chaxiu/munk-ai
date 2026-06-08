from __future__ import annotations

from dataclasses import dataclass

from munk.agent_base.action import DEFAULT_ACTION_TIMEOUT_SEC, ActionExecutor
from munk.agent_base.action.high_level import HighLevelActionService
from munk.app import AppTarget
from munk.config import ResolvedConfig
from munk.config.defaults import DEFAULT_INTERVAL, DEFAULT_RUNNER_MAX_ELEMENTS
from munk.config.resolve import resolve_runtime_config
from munk.device import DeviceDriver, resolve_device_runtime_factory
from munk.paths import export_adb_env
from munk.perception import PerceptionProvider
from munk.runtime_defaults import DEFAULT_ICON_CONF, DEFAULT_MAX_SIDE
from munk.services.perception_runtime import build_perception_provider_for_runtime

INTERACTIVE_SETTLE_TIMEOUT_SEC = 6.0


@dataclass(frozen=True)
class InteractiveSessionContext:
    device: DeviceDriver
    executor: ActionExecutor
    high_level_actions: HighLevelActionService
    perception: PerceptionProvider
    app_target: AppTarget
    device_ref: str | None
    platform: str
    resolved_config: ResolvedConfig
    max_elements: int = DEFAULT_RUNNER_MAX_ELEMENTS
    icon_conf: float = DEFAULT_ICON_CONF
    settle_timeout_sec: float = INTERACTIVE_SETTLE_TIMEOUT_SEC
    settle_poll_interval_sec: float = DEFAULT_INTERVAL


def build_interactive_session_context(
    *,
    resolved_config: ResolvedConfig,
    app_target: AppTarget,
    device_ref: str | None = None,
    max_side: int = DEFAULT_MAX_SIDE,
    icon_conf: float = DEFAULT_ICON_CONF,
    max_elements: int = DEFAULT_RUNNER_MAX_ELEMENTS,
    action_timeout_sec: float = DEFAULT_ACTION_TIMEOUT_SEC,
) -> InteractiveSessionContext:
    runtime = resolve_runtime_config(resolved_config.config)
    export_adb_env()
    factory = resolve_device_runtime_factory(platform=app_target.platform)
    device = factory.create_device(device_ref=device_ref, app_target=app_target)
    perception = build_perception_provider_for_runtime(
        resolved_config.config,
        max_side=max_side,
        icon_conf=icon_conf,
    )
    executor = ActionExecutor(device, action_timeout_sec=action_timeout_sec)
    high_level_actions = HighLevelActionService(device, executor)
    return InteractiveSessionContext(
        device=device,
        executor=executor,
        high_level_actions=high_level_actions,
        perception=perception,
        app_target=app_target,
        device_ref=device_ref,
        platform=app_target.platform,
        resolved_config=resolved_config,
        max_elements=max_elements,
        icon_conf=icon_conf,
        settle_timeout_sec=INTERACTIVE_SETTLE_TIMEOUT_SEC,
        settle_poll_interval_sec=runtime.interval,
    )
