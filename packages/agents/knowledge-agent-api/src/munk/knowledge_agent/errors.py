from __future__ import annotations


class KnowledgeAgentRuntimeError(RuntimeError):
    """Base class for knowledge agent runtime resolution errors."""


class KnowledgeAgentRuntimeUnavailableError(KnowledgeAgentRuntimeError):
    """Raised when no knowledge agent runtime can be resolved."""


class KnowledgeAgentRuntimeConflictError(KnowledgeAgentRuntimeError):
    """Raised when multiple knowledge agent runtimes are installed."""
