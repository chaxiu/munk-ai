from __future__ import annotations

from importlib import import_module

__all__ = [
    "AgentOpenAICompatibleConfig",
    "AgentModelConfig",
    "AgentRole",
    "MunkAgentsConfig",
    "MunkConfig",
    "MUNK_CODE_DEFAULTS",
    "ConfigSourceKind",
    "GeminiSection",
    "LLMProviderKind",
    "OpenAICompatibleSection",
    "PerceptionConfig",
    "ResolvedModelConfig",
    "ResolvedOrchestrationConfig",
    "ResolvedRuntimeConfig",
    "ResolvedConfig",
    "ResolvedConfigFile",
    "default_config_path",
    "load_config_context",
    "load_config_file",
    "load_resolved_config",
    "resolve_openai_compatible_section",
    "resolve_role_model_config",
    "resolve_orchestration_config",
    "resolve_orchestration_policy",
    "resolve_runtime_config",
    "resolve_config_file",
    "resolve_config_path",
    "workspace_config_path",
    "RuntimeConfig",
]

_EXPORTS = {
    "AgentOpenAICompatibleConfig": ("munk.config.schema", "AgentOpenAICompatibleConfig"),
    "AgentModelConfig": ("munk.config.schema", "AgentModelConfig"),
    "AgentRole": ("munk.config.schema", "AgentRole"),
    "MunkAgentsConfig": ("munk.config.schema", "MunkAgentsConfig"),
    "MunkConfig": ("munk.config.schema", "MunkConfig"),
    "MUNK_CODE_DEFAULTS": ("munk.config.defaults", "MUNK_CODE_DEFAULTS"),
    "ConfigSourceKind": ("munk.config.load", "ConfigSourceKind"),
    "GeminiSection": ("munk.config.schema", "GeminiSection"),
    "LLMProviderKind": ("munk.config.schema", "LLMProviderKind"),
    "OpenAICompatibleSection": ("munk.config.schema", "OpenAICompatibleSection"),
    "PerceptionConfig": ("munk.config.schema", "PerceptionConfig"),
    "ResolvedModelConfig": ("munk.config.resolve", "ResolvedModelConfig"),
    "ResolvedOrchestrationConfig": ("munk.config.resolve", "ResolvedOrchestrationConfig"),
    "ResolvedRuntimeConfig": ("munk.config.resolve", "ResolvedRuntimeConfig"),
    "ResolvedConfig": ("munk.config.load", "ResolvedConfig"),
    "ResolvedConfigFile": ("munk.config.load", "ResolvedConfigFile"),
    "default_config_path": ("munk.config.load", "default_config_path"),
    "load_config_context": ("munk.config.load", "load_config_context"),
    "load_config_file": ("munk.config.load", "load_config_file"),
    "load_resolved_config": ("munk.config.load", "load_resolved_config"),
    "resolve_openai_compatible_section": ("munk.config.resolve", "resolve_openai_compatible_section"),
    "resolve_role_model_config": ("munk.config.resolve", "resolve_role_model_config"),
    "resolve_orchestration_config": ("munk.config.resolve", "resolve_orchestration_config"),
    "resolve_orchestration_policy": ("munk.config.resolve", "resolve_orchestration_policy"),
    "resolve_runtime_config": ("munk.config.resolve", "resolve_runtime_config"),
    "resolve_config_file": ("munk.config.load", "resolve_config_file"),
    "resolve_config_path": ("munk.config.load", "resolve_config_path"),
    "workspace_config_path": ("munk.config.load", "workspace_config_path"),
    "RuntimeConfig": ("munk.config.schema", "RuntimeConfig"),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
