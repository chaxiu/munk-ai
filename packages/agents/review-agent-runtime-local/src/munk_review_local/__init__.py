from __future__ import annotations

from importlib import import_module

__all__ = [
    "ReviewFinding",
    "ReviewKnowledgeHit",
    "ReviewRequest",
    "ReviewResult",
    "SuggestedFollowUpCase",
    "build_review_runtime_factory",
]

_EXPORTS = {
    "ReviewFinding": ("munk.reviewing.models", "ReviewFinding"),
    "ReviewKnowledgeHit": ("munk.reviewing.models", "ReviewKnowledgeHit"),
    "ReviewRequest": ("munk.reviewing.models", "ReviewRequest"),
    "ReviewResult": ("munk.reviewing.models", "ReviewResult"),
    "SuggestedFollowUpCase": ("munk.reviewing.models", "SuggestedFollowUpCase"),
    "build_review_runtime_factory": (".runtime", "build_review_runtime_factory"),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
