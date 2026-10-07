from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai._output import OutputSchema, StructuredTextOutputSchema
from pydantic_ai.output import PromptedOutput
from pydantic_ai.profiles import ModelProfile

from munk.config.resolve import ResolvedModelConfig
from munk.config.schema import OpenAICompatibleSection, OutputStrategy


@dataclass(frozen=True)
class StructuredOutputSpec:
    output_type: Any
    system_prompt_suffix: str | None = None


def resolve_output_strategy(value: ResolvedModelConfig | OpenAICompatibleSection | None) -> OutputStrategy:
    if value is None:
        return "auto"
    if isinstance(value, ResolvedModelConfig):
        if value.provider != "openai_compatible":
            return "auto"
        section = value.config_section
        if isinstance(section, OpenAICompatibleSection):
            return section.output_strategy
        return "auto"
    return value.output_strategy


def build_structured_output_spec(output_schema: Any, *, output_strategy: OutputStrategy) -> StructuredOutputSpec:
    if output_strategy != "prompted":
        return StructuredOutputSpec(output_type=output_schema)

    output_type = PromptedOutput(output_schema, template=False)
    built_schema = OutputSchema.build(output_type)
    system_prompt_suffix: str | None = None
    if isinstance(built_schema, StructuredTextOutputSchema) and built_schema.object_def is not None:
        system_prompt_suffix = StructuredTextOutputSchema.build_instructions(
            ModelProfile().prompted_output_template,
            built_schema.object_def,
        ).strip()
    return StructuredOutputSpec(output_type=output_type, system_prompt_suffix=system_prompt_suffix)


def append_system_prompt_suffix(system_prompt: str, suffix: str | None) -> str:
    cleaned_suffix = (suffix or "").strip()
    if not cleaned_suffix:
        return system_prompt
    cleaned_prompt = system_prompt.rstrip()
    if not cleaned_prompt:
        return cleaned_suffix
    return f"{cleaned_prompt}\n\n{cleaned_suffix}"


def build_structured_output_type(output_schema: Any, *, output_strategy: OutputStrategy) -> Any:
    return build_structured_output_spec(output_schema, output_strategy=output_strategy).output_type
