from __future__ import annotations

import json
import logging
from concurrent.futures import Executor, Future
from dataclasses import dataclass, replace

from munk.agent_base import (
    Brain,
    build_pydantic_ai_model,
    check_vision_support,
    resolve_output_strategy,
)
from munk.agent_base.action import ActionExecutor
from munk.agent_base.action.high_level import HighLevelActionService
from munk.app_knowledge import AppKnowledgeImportDocument
from munk.device import DeviceDriver, SupportsRuntimeLogs
from munk.perception import PerceptionProvider
from munk.running import (
    RunnerManagedPaths,
    RunnerRequest,
    RunnerRuntimeContext,
    RuntimeOverrideValue,
    build_case_brief,
)
from munk.shared_tools import KnowledgeToolProvider

from munk.app_assets.storage import AppRegistry
from munk.config import ResolvedConfig, resolve_role_model_config
from munk.services.errors import ConfigValidationError, VisionPreflightError
from munk.services.events import RunEventSink
from munk.services.knowledge import build_knowledge_provider_from_document, load_app_knowledge_document
from munk.services.models import RunPaths, RunStartParams

from .brain.context_prep_agent import ContextPrepAgent, build_context_prep_fallback, build_knowledge_card_catalog_text
from .brain.context_prep_models import (
    ContextPrepBundleToolResult,
    ContextPrepKnowledgeItem,
    ContextPrepOutput,
    ContextPrepSelectionItem,
)
from .brain.context_prep_tools import get_knowledge_card_bundle_payload
from .brain.pydantic_runner import PydanticAiRunnerBrain
from .monitor.simple import SimpleMonitor
from .runtime_logs import RunLogCollector

logger = logging.getLogger(__name__)


@dataclass
class RunContext:
    request: RunnerRequest
    params: RunStartParams
    paths: RunPaths
    device: DeviceDriver
    executor: ActionExecutor
    high_level_actions: HighLevelActionService
    monitor: SimpleMonitor
    perception: PerceptionProvider
    brain: Brain
    knowledge_tools: KnowledgeToolProvider | None = None
    app_introduction: str | None = None
    context_prep_agent: ContextPrepAgent | None = None
    context_prep_executor: Executor | None = None
    context_prep_future: Future[ContextPrepOutput] | None = None
    context_prep_output: ContextPrepOutput | None = None
    context_prep_selection_source: str | None = None
    prepared_knowledge_bundle: tuple[ContextPrepKnowledgeItem, ...] = ()
    context_prep_missing_card_ids: tuple[str, ...] = ()
    log_collector: RunLogCollector | None = None


def load_runner_knowledge_tools(request: RunnerRequest) -> KnowledgeToolProvider:
    registry = AppRegistry(request.assets_root)
    try:
        profile = registry.load(request.app_id)
    except FileNotFoundError:
        return build_knowledge_provider_from_document(AppKnowledgeImportDocument(app_id=request.app_id, cards=[]))
    document = load_app_knowledge_document(
        request.app_id,
        registry=registry,
        ref=profile.app_knowledge_ref,
    )
    if document is None:
        document = AppKnowledgeImportDocument(app_id=request.app_id, cards=[])
    return build_knowledge_provider_from_document(document)


def load_runner_app_introduction(request: RunnerRequest) -> str | None:
    registry = AppRegistry(request.assets_root)
    try:
        profile = registry.load(request.app_id)
    except FileNotFoundError:
        return None
    introduction_path = registry.introduction_path(request.app_id, ref=profile.app_introduction_ref)
    if not introduction_path.exists():
        return None
    try:
        return registry.load_introduction(request.app_id, ref=profile.app_introduction_ref)
    except FileNotFoundError:
        return None


def build_local_runner_context(
    *,
    request: RunnerRequest,
    runtime_context: RunnerRuntimeContext,
    resolved_config: ResolvedConfig,
    event_sink: RunEventSink | None = None,
) -> RunContext:
    params = build_run_start_params(request=request, resolved_config=resolved_config)
    paths = build_run_paths_from_managed_paths(runtime_context.managed_paths)
    runner_config = resolve_role_model_config(params.resolved_config.config, role="runner")
    if runner_config is None:
        raise ConfigValidationError("config must include a valid runner model configuration")
    device = runtime_context.device

    log_collector: RunLogCollector | None = None
    if isinstance(device, SupportsRuntimeLogs) and paths.runtime_logs_dir is not None:
        try:
            log_collector = RunLogCollector(device, logs_dir=paths.runtime_logs_dir)
            log_collector.start()
        except Exception as exc:  # noqa: BLE001
            logger.warning("runtime_log_session_start_failed error=%s", exc)
            log_collector = None

    try:
        # Use a self-generated probe image so vision preflight stays independent
        # from device state and screenshot-specific variability.
        check_vision_support(runner_config, config=params.resolved_config.config)
    except RuntimeError as exc:
        raise VisionPreflightError(str(exc)) from exc

    context_prep_model = build_pydantic_ai_model(runner_config, config=params.resolved_config.config)
    runner_model = build_pydantic_ai_model(runner_config, config=params.resolved_config.config)
    knowledge_tools = load_runner_knowledge_tools(request)
    app_introduction = load_runner_app_introduction(request)
    context_prep_agent = ContextPrepAgent(
        model=context_prep_model,
        output_strategy=resolve_output_strategy(runner_config),
        max_tokens=params.max_tokens,
        temperature=params.temperature,
        top_p=0.9,
    )
    brain: Brain = PydanticAiRunnerBrain(
        app_id=request.app_id,
        knowledge_tools=knowledge_tools,
        case_brief=build_case_brief(request.case),
        model=runner_model,
        output_strategy=resolve_output_strategy(runner_config),
        paths=paths,
        event_sink=event_sink,
        max_tokens=params.max_tokens,
        temperature=params.temperature,
        top_p=0.9,
        vl_max_side=params.vl_max_side,
        max_elements=params.runner_max_elements,
        platform=request.app_target.platform,
    )

    perception = runtime_context.perception
    executor = ActionExecutor(device)
    high_level_actions = HighLevelActionService(device, executor)
    monitor = SimpleMonitor(max_steps=params.max_steps, max_duration=params.max_seconds)
    return RunContext(
        request,
        params,
        paths,
        device,
        executor,
        high_level_actions,
        monitor,
        perception,
        brain,
        knowledge_tools,
        app_introduction,
        context_prep_agent,
        None,
        None,
        None,
        None,
        (),
        (),
        log_collector,
    )


def prepare_runner_context(context: RunContext) -> ContextPrepOutput:
    selection_source = "primary"
    try:
        if context.context_prep_agent is None:
            output = build_context_prep_fallback("context prep agent unavailable")
            selection_source = "fallback_default"
        else:
            output = context.context_prep_agent.prepare_with_fallback(
                app_introduction=context.app_introduction,
                case_brief=build_case_brief(context.request.case),
                knowledge_tools=context.knowledge_tools or build_knowledge_provider_from_document(
                    AppKnowledgeImportDocument(app_id=context.request.app_id, cards=[])
                ),
            )
            if output.fallback_reason is not None:
                selection_source = "fallback_prompted"
    except Exception as exc:  # noqa: BLE001
        logger.warning("context_prep_failed error=%s", exc)
        output = build_context_prep_fallback(f"context prep failed: {exc}")
        selection_source = "fallback_default"
    output, selection_source = normalize_context_prep_output(
        context,
        output,
        selection_source=selection_source,
    )
    context.context_prep_output = output
    context.context_prep_selection_source = selection_source
    bundle_result = build_prepared_knowledge_bundle(context, output)
    context.prepared_knowledge_bundle = tuple(bundle_result.items)
    context.context_prep_missing_card_ids = tuple(bundle_result.missing_card_ids)
    if bundle_result.missing_card_ids and output.fallback_reason is None:
        output = output.model_copy(
            update={
                "fallback_reason": f"context prep bundle missing cards: {', '.join(bundle_result.missing_card_ids)}",
            }
        )
        context.context_prep_output = output
    write_context_prep_artifact(context, output)
    return output


def build_prepared_knowledge_bundle(
    context: RunContext,
    output: ContextPrepOutput,
) -> ContextPrepBundleToolResult:
    selected_card_ids = [item.card_id for item in output.selected_entries]
    if not selected_card_ids or context.knowledge_tools is None:
        return ContextPrepBundleToolResult(items=[], missing_card_ids=[])
    return get_knowledge_card_bundle_payload(knowledge_tools=context.knowledge_tools, card_ids=selected_card_ids)


def normalize_context_prep_output(
    context: RunContext,
    output: ContextPrepOutput,
    *,
    selection_source: str,
) -> tuple[ContextPrepOutput, str]:
    valid_card_ids = {
        card.card_id
        for card in (context.knowledge_tools.list(limit=1000) if context.knowledge_tools is not None else [])
    }
    normalized_entries: list[ContextPrepSelectionItem] = []
    seen_card_ids: set[str] = set()
    invalid_card_ids: list[str] = []
    for item in output.selected_entries:
        card_id = item.card_id.strip()
        if card_id in seen_card_ids:
            continue
        if card_id not in valid_card_ids:
            invalid_card_ids.append(card_id)
            continue
        normalized_entries.append(item.model_copy(update={"card_id": card_id}))
        seen_card_ids.add(card_id)
        if len(normalized_entries) >= 3:
            break
    if normalized_entries == output.selected_entries and not invalid_card_ids:
        return output, selection_source
    if normalized_entries:
        updated_reason = output.fallback_reason
        if invalid_card_ids:
            suffix = f"invalid fallback card_ids filtered: {', '.join(invalid_card_ids)}"
            updated_reason = f"{updated_reason}; {suffix}" if updated_reason else suffix
        return (
            output.model_copy(
                update={
                    "selected_entries": normalized_entries,
                    "fallback_reason": updated_reason,
                }
            ),
            selection_source,
        )
    fallback_reason = output.fallback_reason or "context prep fallback produced no valid keys"
    if invalid_card_ids:
        fallback_reason = f"{fallback_reason}; invalid fallback card_ids: {', '.join(invalid_card_ids)}"
    return build_context_prep_fallback(fallback_reason), "fallback_default"


def write_context_prep_artifact(context: RunContext, output: ContextPrepOutput) -> None:
    artifact_path = context.paths.context_prep_path
    if artifact_path is None:
        return
    payload = {
        "app_id": context.request.app_id,
        "introduction_present": bool(context.app_introduction and context.app_introduction.strip()),
        "knowledge_card_catalog_text": build_knowledge_card_catalog_text(
            context.knowledge_tools or build_knowledge_provider_from_document(
                AppKnowledgeImportDocument(app_id=context.request.app_id, cards=[])
            )
        ),
        "selected_entries": [item.model_dump(mode="python") for item in output.selected_entries],
        "knowledge_bundle": [item.model_dump(mode="python") for item in context.prepared_knowledge_bundle],
        "prep_summary": output.prep_summary,
        "missing_card_ids": list(context.context_prep_missing_card_ids),
        "fallback_reason": output.fallback_reason,
        "selection_source": context.context_prep_selection_source,
    }
    artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_run_paths_from_managed_paths(paths: RunnerManagedPaths) -> RunPaths:
    return RunPaths(
        run_dir=paths.root_dir,
        log_path=paths.root_dir / "run.log",
        raw_dir=paths.raw_dir,
        annotated_dir=paths.annotated_dir,
        runtime_logs_dir=paths.runtime_logs_dir,
        observation_frames_dir=paths.observation_frames_dir,
        observation_diffs_dir=paths.observation_diffs_dir,
        observation_tree_dir=paths.observation_tree_dir,
        case_path=paths.request_dump_path,
        result_path=paths.root_dir / "result.json",
        decision_trace_path=paths.decision_trace_path,
        runner_history_path=paths.runner_history_path,
        runner_memory_path=paths.runner_memory_path,
        llm_transcript_path=paths.llm_transcript_path,
        context_prep_path=paths.context_prep_path,
    )


def build_run_start_params(*, request: RunnerRequest, resolved_config: ResolvedConfig) -> RunStartParams:
    params = RunStartParams(
        resolved_config=resolved_config,
        app_target=request.app_target,
        device_ref=request.device_ref,
    )
    for key, value in request.runtime_overrides.items():
        params = apply_runtime_override(params, key, value)
    return params


def apply_runtime_override(
    params: RunStartParams,
    key: str,
    value: RuntimeOverrideValue,
) -> RunStartParams:
    if key in {"device_ref", "goal", "app_id", "plan_id", "case_id"}:
        raise ValueError(f"{key} is managed by case context and cannot be overridden")
    if key == "max_steps":
        return replace(params, max_steps=require_int_override(key, value))
    if key in {"max_seconds", "interval", "settle_timeout", "initial_ready_timeout_sec", "icon_conf", "temperature"}:
        return replace(params, **{key: require_float_override(key, value)})
    if key in {"max_side", "max_tokens", "vl_max_side", "runner_max_elements"}:
        return replace(params, **{key: require_int_override(key, value)})
    raise ValueError(f"unsupported runtime override: {key}")


def require_int_override(key: str, value: RuntimeOverrideValue) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"runtime override '{key}' must be an integer")
    return value


def require_float_override(key: str, value: RuntimeOverrideValue) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"runtime override '{key}' must be a number")
    return float(value)
