from __future__ import annotations

from importlib import import_module
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

__all__ = [
    "ChangePlanInput",
    "CoreCaseRegistry",
    "PlanCaseIndexStore",
    "PlanGenerationResult",
    "PlanMutationService",
    "PlanService",
    "PlanSnapshot",
    "PlanStore",
    "RequirementInput",
    "RequirementPlan",
]

_EXPORTS = {
    "ChangePlanInput": ("munk.planning.models", "ChangePlanInput"),
    "CoreCaseRegistry": (".storage", "CoreCaseRegistry"),
    "PlanCaseIndexStore": (".index_store", "PlanCaseIndexStore"),
    "PlanGenerationResult": (".service", "PlanGenerationResult"),
    "PlanMutationService": (".plan_mutation_service", "PlanMutationService"),
    "PlanService": (".service", "PlanService"),
    "PlanSnapshot": ("munk.planning.models", "PlanSnapshot"),
    "PlanStore": (".storage", "PlanStore"),
    "RequirementInput": ("munk.planning.models", "RequirementInput"),
    "RequirementPlan": ("munk.planning.models", "RequirementPlan"),
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
