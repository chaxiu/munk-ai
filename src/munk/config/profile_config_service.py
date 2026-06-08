from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, cast

import yaml

from munk.adapters.local_api.config_models import (
    AgentConfigEditor,
    GeminiSectionEditor,
    OpenAICompatibleSectionEditor,
    OrchestrationConfigEditor,
    ProxyConfigEditor,
    RuntimeConfigEditor,
    SettingsAgentsEditor,
    SettingsConfigUpsertRequest,
)
from munk.config.load import profile_config_path, resolve_config_file
from munk.config.schema import LLMProviderKind, MunkConfig, OutputStrategy

AgentRoleName = Literal["plan", "runner", "judge", "review", "analysis"]
_AGENT_ROLES: tuple[AgentRoleName, ...] = ("plan", "runner", "judge", "review", "analysis")


class ProfileConfigService:
    def __init__(
        self,
        *,
        path: Path | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve() if workspace_root is not None else Path.cwd().resolve()
        self._path = path.resolve() if path is not None else self._resolve_active_config_path()

    @property
    def path(self) -> Path:
        return self._path

    def _resolve_active_config_path(self) -> Path:
        resolved = resolve_config_file(None, workspace_root=self._workspace_root)
        if resolved is not None:
            return resolved.path.resolve()
        return profile_config_path().resolve()

    def load_editor_state(self) -> dict[str, Any]:
        raw_payload = self._load_raw_yaml_dict()
        MunkConfig.model_validate(raw_payload)
        return self._build_editor_payload(raw_payload=raw_payload, file_exists=self.path.exists())

    def save_editor_state(self, request: SettingsConfigUpsertRequest) -> dict[str, Any]:
        previous_payload = self._load_raw_yaml_dict()
        payload = self._build_yaml_payload(request=request, previous_payload=previous_payload)
        MunkConfig.model_validate(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self._dump_yaml(payload), encoding="utf-8")
        return self._build_editor_payload(raw_payload=payload, file_exists=True)

    def _load_raw_yaml_dict(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError(f"config root must be a mapping: {self.path}")
        return cast(dict[str, Any], raw)

    def _build_editor_payload(self, *, raw_payload: dict[str, Any], file_exists: bool) -> dict[str, Any]:
        agents_payload = raw_payload.get("agents")
        runtime_payload = raw_payload.get("runtime")
        provider = raw_payload.get("provider")
        return {
            "config_path": str(self.path),
            "file_exists": file_exists,
            "provider": provider if provider in {"openai_compatible", "gemini"} else "openai_compatible",
            "openai_compatible": self._build_openai_editor(raw_payload.get("openai_compatible")),
            "gemini": self._build_gemini_editor(raw_payload.get("gemini")),
            "agents": self._build_agents_editor(agents_payload),
            "proxy": self._build_proxy_editor(raw_payload.get("proxy")),
            "runtime": self._build_runtime_editor(runtime_payload),
            "orchestration": self._build_orchestration_editor(raw_payload.get("orchestration")),
        }

    def _build_agents_editor(self, agents_payload: Any) -> SettingsAgentsEditor:
        role_payloads = cast(dict[str, Any], agents_payload) if isinstance(agents_payload, dict) else {}
        return SettingsAgentsEditor(
            plan=self._build_agent_editor(role_payloads.get("plan")),
            runner=self._build_agent_editor(role_payloads.get("runner")),
            judge=self._build_agent_editor(role_payloads.get("judge")),
            review=self._build_agent_editor(role_payloads.get("review")),
            analysis=self._build_agent_editor(role_payloads.get("analysis")),
        )

    def _build_agent_editor(self, value: Any) -> AgentConfigEditor:
        if not isinstance(value, dict):
            return AgentConfigEditor(enabled=False)
        provider = self._string_or_none(value.get("provider"))
        normalized_provider: LLMProviderKind | None = None
        if provider in {"openai_compatible", "gemini"}:
            normalized_provider = cast(LLMProviderKind, provider)
        return AgentConfigEditor(
            enabled=True,
            provider=normalized_provider,
            openai_compatible=self._build_openai_editor(value.get("openai_compatible")),
            gemini=self._build_gemini_editor(value.get("gemini")),
        )

    def _build_openai_editor(self, value: Any) -> OpenAICompatibleSectionEditor:
        payload = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        return OpenAICompatibleSectionEditor(
            configured=isinstance(value, dict),
            base_url=self._string_or_none(payload.get("base_url")),
            model=self._string_or_none(payload.get("model")),
            timeout_sec=self._float_or_none(payload.get("timeout_sec")),
            extra_headers=self._coerce_string_dict(payload.get("extra_headers")),
            output_strategy=self._openai_output_strategy_or_default(payload.get("output_strategy")),
            thinking=self._bool_or_none(payload.get("thinking")),
            api_key=None,
            api_key_configured=bool(self._string_or_none(payload.get("api_key"))),
        )

    def _build_gemini_editor(self, value: Any) -> GeminiSectionEditor:
        payload = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        return GeminiSectionEditor(
            configured=isinstance(value, dict),
            model=self._string_or_none(payload.get("model")),
            api_key=None,
            api_key_configured=bool(self._string_or_none(payload.get("api_key"))),
            vertexai=bool(payload.get("vertexai", False)),
            project=self._string_or_none(payload.get("project")),
            location=self._string_or_none(payload.get("location")),
            base_url=self._string_or_none(payload.get("base_url")),
            timeout_sec=self._float_or_none(payload.get("timeout_sec")),
        )

    def _build_runtime_editor(self, value: Any) -> RuntimeConfigEditor:
        payload = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        return RuntimeConfigEditor(
            max_tokens=self._int_or_none(payload.get("max_tokens")),
            temperature=self._float_or_none(payload.get("temperature")),
            max_steps=self._int_or_none(payload.get("max_steps")),
            max_seconds=self._float_or_none(payload.get("max_seconds")),
            interval=self._float_or_none(payload.get("interval")),
            settle_timeout=self._float_or_none(payload.get("settle_timeout")),
            max_side=self._int_or_none(payload.get("max_side")),
            vl_max_side=self._int_or_none(payload.get("vl_max_side")),
            icon_conf=self._float_or_none(payload.get("icon_conf")),
        )

    def _build_orchestration_editor(self, value: Any) -> OrchestrationConfigEditor:
        payload = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        max_retry_attempts = self._int_or_none(payload.get("max_retry_attempts"))
        allow_retry_on_failed = self._bool_or_none(payload.get("allow_retry_on_failed"))
        allow_retry_on_inconclusive = self._bool_or_none(payload.get("allow_retry_on_inconclusive"))
        escalate_after_max_attempts = self._bool_or_none(payload.get("escalate_after_max_attempts"))
        return OrchestrationConfigEditor(
            max_retry_attempts=max_retry_attempts if max_retry_attempts is not None else 0,
            allow_retry_on_failed=allow_retry_on_failed if allow_retry_on_failed is not None else True,
            allow_retry_on_inconclusive=(
                allow_retry_on_inconclusive if allow_retry_on_inconclusive is not None else True
            ),
            escalate_after_max_attempts=(
                escalate_after_max_attempts if escalate_after_max_attempts is not None else False
            ),
        )

    def _build_proxy_editor(self, value: Any) -> ProxyConfigEditor:
        payload = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        return ProxyConfigEditor(
            enabled=bool(payload.get("enabled", False)),
            url=self._string_or_none(payload.get("url")),
            no_proxy=self._coerce_string_list(payload.get("no_proxy")),
        )

    def _build_yaml_payload(
        self,
        *,
        request: SettingsConfigUpsertRequest,
        previous_payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": request.provider,
        }
        openai_payload = self._build_openai_section_payload(
            request.openai_compatible,
            previous_section=previous_payload.get("openai_compatible"),
        )
        gemini_payload = self._build_gemini_section_payload(
            request.gemini,
            previous_section=previous_payload.get("gemini"),
        )
        if request.provider == "openai_compatible" and openai_payload is None:
            raise ValueError("global openai_compatible section is required when provider=openai_compatible")
        if request.provider == "gemini" and gemini_payload is None:
            raise ValueError("global gemini section is required when provider=gemini")
        if openai_payload is not None:
            payload["openai_compatible"] = openai_payload
        if gemini_payload is not None:
            payload["gemini"] = gemini_payload

        previous_agents = previous_payload.get("agents")
        previous_agent_payloads = cast(dict[str, Any], previous_agents) if isinstance(previous_agents, dict) else {}
        agents_payload: dict[str, Any] = {}
        for role in _AGENT_ROLES:
            editor = getattr(request.agents, role)
            role_payload = self._build_agent_payload(
                editor,
                previous_section=previous_agent_payloads.get(role),
                role=role,
            )
            if role_payload is not None:
                agents_payload[role] = role_payload
        if agents_payload:
            payload["agents"] = agents_payload

        runtime_payload = self._build_runtime_payload(request.runtime)
        if runtime_payload:
            payload["runtime"] = runtime_payload
        orchestration_payload = self._build_orchestration_payload(request.orchestration)
        if orchestration_payload:
            payload["orchestration"] = orchestration_payload
        proxy_payload = self._build_proxy_payload(request.proxy)
        if proxy_payload is not None:
            payload["proxy"] = proxy_payload
        return payload

    def _build_agent_payload(
        self,
        editor: AgentConfigEditor,
        *,
        previous_section: Any,
        role: AgentRoleName,
    ) -> dict[str, Any] | None:
        if not editor.enabled:
            return None
        if editor.provider is None:
            raise ValueError(f"agent '{role}' provider is required when override is enabled")
        previous_payload = cast(dict[str, Any], previous_section) if isinstance(previous_section, dict) else {}
        openai_payload = self._build_openai_section_payload(
            editor.openai_compatible,
            previous_section=previous_payload.get("openai_compatible"),
        )
        gemini_payload = self._build_gemini_section_payload(
            editor.gemini,
            previous_section=previous_payload.get("gemini"),
        )
        if editor.provider == "openai_compatible" and openai_payload is None:
            raise ValueError(f"agent '{role}' openai_compatible section is required when provider=openai_compatible")
        if editor.provider == "gemini" and gemini_payload is None:
            raise ValueError(f"agent '{role}' gemini section is required when provider=gemini")
        payload: dict[str, Any] = {"provider": editor.provider}
        if openai_payload is not None:
            payload["openai_compatible"] = openai_payload
        if gemini_payload is not None:
            payload["gemini"] = gemini_payload
        return payload

    def _build_openai_section_payload(
        self,
        editor: OpenAICompatibleSectionEditor | None,
        *,
        previous_section: Any,
    ) -> dict[str, Any] | None:
        if editor is None or not editor.configured:
            return None
        payload: dict[str, Any] = {}
        if editor.base_url:
            payload["base_url"] = editor.base_url.strip()
        if editor.model:
            payload["model"] = editor.model.strip()
        if editor.timeout_sec is not None:
            payload["timeout_sec"] = editor.timeout_sec
        payload["extra_headers"] = dict(editor.extra_headers)
        payload["output_strategy"] = self._openai_output_strategy_or_default(editor.output_strategy)
        if editor.thinking is not None:
            payload["thinking"] = editor.thinking
        previous_payload = cast(dict[str, Any], previous_section) if isinstance(previous_section, dict) else {}
        api_key = self._merge_secret_value(editor.api_key, previous_payload.get("api_key"))
        if api_key is not None:
            payload["api_key"] = api_key
        return payload

    def _build_gemini_section_payload(
        self,
        editor: GeminiSectionEditor | None,
        *,
        previous_section: Any,
    ) -> dict[str, Any] | None:
        if editor is None or not editor.configured:
            return None
        payload: dict[str, Any] = {"vertexai": editor.vertexai}
        if editor.model:
            payload["model"] = editor.model.strip()
        if editor.project:
            payload["project"] = editor.project.strip()
        if editor.location:
            payload["location"] = editor.location.strip()
        if editor.base_url:
            payload["base_url"] = editor.base_url.strip()
        if editor.timeout_sec is not None:
            payload["timeout_sec"] = editor.timeout_sec
        previous_payload = cast(dict[str, Any], previous_section) if isinstance(previous_section, dict) else {}
        api_key = self._merge_secret_value(editor.api_key, previous_payload.get("api_key"))
        if api_key is not None:
            payload["api_key"] = api_key
        return payload

    def _build_runtime_payload(self, editor: RuntimeConfigEditor) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if editor.max_tokens is not None:
            payload["max_tokens"] = editor.max_tokens
        if editor.temperature is not None:
            payload["temperature"] = editor.temperature
        if editor.max_steps is not None:
            payload["max_steps"] = editor.max_steps
        if editor.max_seconds is not None:
            payload["max_seconds"] = editor.max_seconds
        if editor.interval is not None:
            payload["interval"] = editor.interval
        if editor.settle_timeout is not None:
            payload["settle_timeout"] = editor.settle_timeout
        if editor.max_side is not None:
            payload["max_side"] = editor.max_side
        if editor.vl_max_side is not None:
            payload["vl_max_side"] = editor.vl_max_side
        if editor.icon_conf is not None:
            payload["icon_conf"] = editor.icon_conf
        return payload

    def _build_orchestration_payload(self, editor: OrchestrationConfigEditor) -> dict[str, Any]:
        return {
            "max_retry_attempts": editor.max_retry_attempts,
            "allow_retry_on_failed": editor.allow_retry_on_failed,
            "allow_retry_on_inconclusive": editor.allow_retry_on_inconclusive,
            "escalate_after_max_attempts": editor.escalate_after_max_attempts,
        }

    def _build_proxy_payload(self, editor: ProxyConfigEditor) -> dict[str, Any] | None:
        url = self._string_or_none(editor.url)
        no_proxy = self._normalize_no_proxy(editor.no_proxy)
        if not editor.enabled and url is None and not no_proxy:
            return None
        if editor.enabled and url is None:
            raise ValueError("proxy url is required when proxy is enabled")
        payload: dict[str, Any] = {"enabled": bool(editor.enabled)}
        if url is not None:
            payload["url"] = url
        if no_proxy:
            payload["no_proxy"] = no_proxy
        return payload

    def _dump_yaml(self, payload: dict[str, Any]) -> str:
        return yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)

    @staticmethod
    def _merge_secret_value(new_value: str | None, previous_value: Any) -> str | None:
        normalized_new = ProfileConfigService._string_or_none(new_value)
        if normalized_new:
            return normalized_new
        previous = ProfileConfigService._string_or_none(previous_value)
        if previous:
            return previous
        return None

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return None

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    @staticmethod
    def _bool_or_none(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        return None

    @staticmethod
    def _coerce_string_dict(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        typed_value = cast(dict[Any, Any], value)
        result: dict[str, str] = {}
        for key, item in typed_value.items():
            if isinstance(key, str) and isinstance(item, str):
                result[key] = item
        return result

    @staticmethod
    def _coerce_string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        typed_value = cast(list[Any], value)
        result: list[str] = []
        for item in typed_value:
            normalized = ProfileConfigService._string_or_none(item)
            if normalized is not None:
                result.append(normalized)
        return result

    @staticmethod
    def _normalize_no_proxy(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = ProfileConfigService._string_or_none(value)
            if normalized is None:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(normalized)
        return result

    @staticmethod
    def _openai_output_strategy_or_default(value: Any) -> OutputStrategy:
        if value == "prompted":
            return "prompted"
        return "auto"
