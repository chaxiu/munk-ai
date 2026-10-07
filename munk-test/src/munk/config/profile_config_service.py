from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal, cast

import yaml

from munk.adapters.local_api.config_models import (
    AgentConfigEditor,
    GeminiSectionEditor,
    HttpBaseConfigEditor,
    IOSBridgeConfigEditor,
    OpenAICompatibleSectionEditor,
    OrchestrationConfigEditor,
    ProxyConfigEditor,
    RuntimeConfigEditor,
    SettingsAgentsEditor,
    SettingsConfigUpsertRequest,
    TestEnvConfigEditor,
)
from munk.config.defaults import MUNK_CODE_DEFAULTS
from munk.config.layered import (
    build_layered_document,
    deep_merge,
    effective_config_dict,
    ensure_no_secrets_in_shared,
    parse_layered_document,
    read_shared_for_sync,
    replace_shared_in_document,
    sanitize_shared_for_sync,
    split_flat_to_layered,
)
from munk.config.load import profile_config_path, resolve_config_file
from munk.config.resolve import RuntimeOverridePatch
from munk.config.schema import LLMProviderKind, MunkConfig, OutputStrategy, SettleMode

AgentRoleName = Literal["plan", "runner", "judge", "review", "analysis"]
_AGENT_ROLES: tuple[AgentRoleName, ...] = ("plan", "runner", "judge", "review", "analysis")
_SETTINGS_AGENT_ROLES = frozenset(_AGENT_ROLES)


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
        effective = effective_config_dict(raw_payload)
        MunkConfig.model_validate(effective)
        return self._build_editor_payload(raw_payload=effective, file_exists=self.path.exists())

    def save_editor_state(self, request: SettingsConfigUpsertRequest) -> dict[str, Any]:
        previous_raw = self._load_raw_yaml_dict()
        previous_effective = effective_config_dict(previous_raw)
        flat_payload = self._build_yaml_payload(request=request, previous_payload=previous_effective)
        MunkConfig.model_validate(flat_payload)
        layered = self._to_layered_document(flat_payload=flat_payload, previous_raw=previous_raw)
        ensure_no_secrets_in_shared(layered.get("shared", {}))
        MunkConfig.model_validate(effective_config_dict(layered))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self._dump_yaml(layered), encoding="utf-8")
        return self._build_editor_payload(
            raw_payload=effective_config_dict(layered),
            file_exists=True,
        )

    def export_shared_config(self) -> dict[str, Any]:
        """Return sanitized shared section for cloud Bundle team_config."""
        return read_shared_for_sync(self._load_raw_yaml_dict())

    def apply_shared_config(self, team_config: dict[str, Any]) -> dict[str, Any]:
        """Replace shared from cloud team_config; preserve local. Returns editor state."""
        previous_raw = self._load_raw_yaml_dict()
        layered = replace_shared_in_document(previous_raw, team_config)
        ensure_no_secrets_in_shared(layered.get("shared", {}))
        MunkConfig.model_validate(effective_config_dict(layered))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self._dump_yaml(layered), encoding="utf-8")
        return self._build_editor_payload(
            raw_payload=effective_config_dict(layered),
            file_exists=True,
        )

    def _to_layered_document(
        self,
        *,
        flat_payload: dict[str, Any],
        previous_raw: dict[str, Any],
    ) -> dict[str, Any]:
        new_shared, new_local = split_flat_to_layered(flat_payload)
        previous_shared, previous_local = parse_layered_document(previous_raw)
        shared = self._preserve_unmodeled_shared(previous_shared, new_shared)
        local = self._preserve_unmodeled_local(previous_local, new_local)
        return build_layered_document(sanitize_shared_for_sync(shared), local)

    @staticmethod
    def _preserve_unmodeled_shared(
        previous_shared: dict[str, Any],
        new_shared: dict[str, Any],
    ) -> dict[str, Any]:
        result = deepcopy(new_shared)
        # Settings does not edit perception; keep previous shared perception.
        if "perception" in previous_shared and "perception" not in result:
            result["perception"] = deepcopy(previous_shared["perception"])
        previous_agents = previous_shared.get("agents")
        if isinstance(previous_agents, dict):
            agents = cast(dict[str, Any], deepcopy(result.get("agents") or {}))
            for role, payload in previous_agents.items():
                if role in _SETTINGS_AGENT_ROLES:
                    continue
                if role not in agents:
                    agents[role] = deepcopy(payload)
            if agents:
                result["agents"] = agents
        return result

    @staticmethod
    def _preserve_unmodeled_local(
        previous_local: dict[str, Any],
        new_local: dict[str, Any],
    ) -> dict[str, Any]:
        result = deepcopy(new_local)
        if "perception" in previous_local:
            previous_perception = cast(dict[str, Any], previous_local["perception"])
            current = cast(dict[str, Any], result.get("perception") or {})
            result["perception"] = deep_merge(previous_perception, current)
        # Preserve unknown local top-level keys Settings never writes.
        settings_local_keys = {
            "proxy",
            "ios_bridge",
            "openai_compatible",
            "gemini",
            "agents",
            "perception",
        }
        for key, value in previous_local.items():
            if key in settings_local_keys:
                continue
            if key not in result:
                result[key] = deepcopy(value)
        return result

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
            "ios_bridge": self._build_ios_bridge_editor(raw_payload.get("ios_bridge")),
            "test_env": self._build_test_env_editor(raw_payload.get("test_env")),
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
            credentials_path=self._string_or_none(payload.get("credentials_path")),
            base_url=self._string_or_none(payload.get("base_url")),
            timeout_sec=self._float_or_none(payload.get("timeout_sec")),
        )

    def _build_runtime_editor(self, value: Any) -> RuntimeConfigEditor:
        payload = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        runtime_values = asdict(MUNK_CODE_DEFAULTS.runtime)
        runtime_values.update(RuntimeOverridePatch.from_mapping(payload).to_override_dict())
        editor_values = {key: runtime_values[key] for key in RuntimeConfigEditor.model_fields}
        editor_values["settle_mode"] = cast(SettleMode, editor_values["settle_mode"])
        return RuntimeConfigEditor.model_validate(editor_values)

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

    def _build_ios_bridge_editor(self, value: Any) -> IOSBridgeConfigEditor:
        payload = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        return IOSBridgeConfigEditor(
            sudo_enabled=bool(payload.get("sudo_enabled", False)),
            sudo_password=None,
            sudo_password_configured=bool(self._string_or_none(payload.get("sudo_password"))),
        )

    def _build_test_env_editor(self, value: Any) -> TestEnvConfigEditor:
        payload = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        bases_payload = payload.get("bases")
        bases: dict[str, HttpBaseConfigEditor] = {}
        if isinstance(bases_payload, dict):
            typed_bases = cast(dict[Any, Any], bases_payload)
            for name, base_value in typed_bases.items():
                normalized_name = self._string_or_none(name)
                if normalized_name is None:
                    continue
                base_payload = cast(dict[str, Any], base_value) if isinstance(base_value, dict) else {}
                bases[normalized_name] = HttpBaseConfigEditor(
                    url=self._string_or_none(base_payload.get("url")),
                    headers=self._coerce_nonempty_string_dict(base_payload.get("headers")),
                )
        return TestEnvConfigEditor(
            bases=bases,
            allowed_exec=self._normalize_allowed_exec(payload.get("allowed_exec")),
        )

    def _build_yaml_payload(
        self,
        *,
        request: SettingsConfigUpsertRequest,
        previous_payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"provider": request.provider}
        self._apply_provider_sections(payload, request=request, previous_payload=previous_payload)
        agents_payload = self._build_agents_payload(request=request, previous_payload=previous_payload)
        if agents_payload:
            payload["agents"] = agents_payload
        self._apply_runtime_sections(payload, request=request, previous_payload=previous_payload)
        return payload

    def _apply_provider_sections(
        self,
        payload: dict[str, Any],
        *,
        request: SettingsConfigUpsertRequest,
        previous_payload: dict[str, Any],
    ) -> None:
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

    def _build_agents_payload(
        self,
        *,
        request: SettingsConfigUpsertRequest,
        previous_payload: dict[str, Any],
    ) -> dict[str, Any]:
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
        return agents_payload

    def _apply_runtime_sections(
        self,
        payload: dict[str, Any],
        *,
        request: SettingsConfigUpsertRequest,
        previous_payload: dict[str, Any],
    ) -> None:
        runtime_payload = self._build_runtime_payload(request.runtime)
        if runtime_payload:
            payload["runtime"] = runtime_payload
        orchestration_payload = self._build_orchestration_payload(request.orchestration)
        if orchestration_payload:
            payload["orchestration"] = orchestration_payload
        proxy_payload = self._build_proxy_payload(request.proxy)
        if proxy_payload is not None:
            payload["proxy"] = proxy_payload
        ios_bridge_payload = self._build_ios_bridge_payload(request.ios_bridge, previous_payload.get("ios_bridge"))
        if ios_bridge_payload is not None:
            payload["ios_bridge"] = ios_bridge_payload
        test_env_payload = self._build_test_env_payload(request.test_env)
        if test_env_payload is not None:
            payload["test_env"] = test_env_payload

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
        if editor.credentials_path:
            payload["credentials_path"] = editor.credentials_path.strip()
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
        return RuntimeOverridePatch.from_mapping(editor.model_dump(exclude_none=True)).to_override_dict()

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

    def _build_ios_bridge_payload(
        self,
        editor: IOSBridgeConfigEditor,
        previous_section: Any,
    ) -> dict[str, Any] | None:
        previous_payload = cast(dict[str, Any], previous_section) if isinstance(previous_section, dict) else {}
        sudo_password = self._merge_secret_value(editor.sudo_password, previous_payload.get("sudo_password"))
        if not editor.sudo_enabled and sudo_password is None:
            return None
        payload: dict[str, Any] = {"sudo_enabled": bool(editor.sudo_enabled)}
        if sudo_password is not None:
            payload["sudo_password"] = sudo_password
        return payload

    def _build_test_env_payload(self, editor: TestEnvConfigEditor) -> dict[str, Any] | None:
        bases_payload: dict[str, Any] = {}
        for name, base_editor in editor.bases.items():
            normalized_name = self._string_or_none(name)
            if normalized_name is None:
                raise ValueError("test_env.bases keys must not be empty")
            url = self._string_or_none(base_editor.url)
            if url is None:
                raise ValueError(f"test_env.bases['{normalized_name}'].url must not be empty")
            headers = self._coerce_nonempty_string_dict(base_editor.headers)
            base_payload: dict[str, Any] = {"url": url}
            if headers:
                base_payload["headers"] = headers
            bases_payload[normalized_name] = base_payload
        allowed_exec = self._normalize_allowed_exec(editor.allowed_exec)
        if not bases_payload and not allowed_exec:
            return None
        payload: dict[str, Any] = {}
        if bases_payload:
            payload["bases"] = bases_payload
        if allowed_exec:
            payload["allowed_exec"] = allowed_exec
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
    def _coerce_nonempty_string_dict(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        typed_value = cast(dict[Any, Any], value)
        result: dict[str, str] = {}
        for key, item in typed_value.items():
            normalized_key = ProfileConfigService._string_or_none(key)
            normalized_value = ProfileConfigService._string_or_none(item)
            if normalized_key is None or normalized_value is None:
                raise ValueError("test_env headers must contain only non-empty string keys and values")
            result[normalized_key] = normalized_value
        return result

    @staticmethod
    def _normalize_allowed_exec(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        seen: set[str] = set()
        result: list[str] = []
        for item in cast(list[Any], value):
            normalized = ProfileConfigService._string_or_none(item)
            if normalized is None:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
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

    @staticmethod
    def _settle_mode_or_none(value: Any) -> SettleMode | None:
        if value in {"strict", "ratio", "delay"}:
            return value
        return None
