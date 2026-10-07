from __future__ import annotations

from typing import Protocol

from .models import CaseOrchestrationRequest, CaseOrchestrationResult


class OrchestrationEngine(Protocol):
    def execute_case(self, request: CaseOrchestrationRequest) -> CaseOrchestrationResult: ...
