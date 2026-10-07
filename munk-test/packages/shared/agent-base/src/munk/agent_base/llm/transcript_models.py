from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Annotated, Callable, Generator, Literal, TypeAlias, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from munk.token_usage import TokenUsage

ENV_LLM_TRANSCRIPT = "MUNK_LLM_TRANSCRIPT"
JsonValue: TypeAlias = Any


class TranscriptContractModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class LlmRequestTranscriptEntry(TranscriptContractModel):
    timestamp: str
    kind: Literal["llm_request"] = "llm_request"
    provider: str
    model: str
    request_id: str
    method: str
    url: str
    headers: dict[str, JsonValue] = Field(default_factory=dict)
    body: JsonValue = None


class LlmResponseTranscriptEntry(TranscriptContractModel):
    timestamp: str
    kind: Literal["llm_response"] = "llm_response"
    provider: str
    model: str
    request_id: str
    method: str
    url: str
    status_code: int
    headers: dict[str, JsonValue] = Field(default_factory=dict)
    body: JsonValue = None
    token_usage: TokenUsage | None = None


LlmTranscriptEntry: TypeAlias = Annotated[
    LlmRequestTranscriptEntry | LlmResponseTranscriptEntry,
    Field(discriminator="kind"),
]
_TRANSCRIPT_ENTRY_ADAPTER: TypeAdapter[LlmTranscriptEntry] = TypeAdapter(LlmTranscriptEntry)
_TRANSCRIPT_PATH: ContextVar[Path | None] = ContextVar("munk_llm_transcript_path", default=None)
_TRANSCRIPT_OBSERVER: ContextVar[Callable[[LlmTranscriptEntry], None] | None] = ContextVar(
    "munk_llm_transcript_observer",
    default=None,
)


@contextmanager
def llm_transcript_scope(path: Path | None) -> Generator[None, None, None]:
    token = _TRANSCRIPT_PATH.set(path)
    try:
        yield
    finally:
        _TRANSCRIPT_PATH.reset(token)


@contextmanager
def llm_transcript_observer_scope(
    observer: Callable[[LlmTranscriptEntry], None] | None,
) -> Generator[None, None, None]:
    token = _TRANSCRIPT_OBSERVER.set(observer)
    try:
        yield
    finally:
        _TRANSCRIPT_OBSERVER.reset(token)


def get_scoped_transcript_path() -> Path | None:
    return _TRANSCRIPT_PATH.get()


def get_transcript_observer() -> Callable[[LlmTranscriptEntry], None] | None:
    return _TRANSCRIPT_OBSERVER.get()


def parse_llm_transcript_entry(raw: object) -> LlmTranscriptEntry | None:
    try:
        return cast(LlmTranscriptEntry, _TRANSCRIPT_ENTRY_ADAPTER.validate_python(raw))
    except Exception:  # noqa: BLE001
        return None
