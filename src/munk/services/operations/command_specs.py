from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from munk.services.artifact_manifest_models import ReproductionTargetKind
from munk.services.operations.models import OperationKind


@dataclass(frozen=True)
class OperationCommandSpec:
    kind: OperationKind
    cli_args: tuple[str, ...]
    reproduction_target: ReproductionTargetKind | None
    local_api_detach_supported: bool = False


_OPERATION_COMMAND_SPECS: tuple[OperationCommandSpec, ...] = (
    OperationCommandSpec(
        kind="plan",
        cli_args=("plan",),
        reproduction_target="plan",
        local_api_detach_supported=True,
    ),
    OperationCommandSpec(
        kind="run_case",
        cli_args=("run", "case"),
        reproduction_target="run_case",
        local_api_detach_supported=True,
    ),
    OperationCommandSpec(
        kind="run_plan",
        cli_args=("run", "plan"),
        reproduction_target="run_plan",
        local_api_detach_supported=True,
    ),
    OperationCommandSpec(
        kind="run_plans",
        cli_args=("run", "plans"),
        reproduction_target="run_plans",
        local_api_detach_supported=True,
    ),
    OperationCommandSpec(
        kind="verify_change",
        cli_args=("verify", "change"),
        reproduction_target="verify_change",
        local_api_detach_supported=True,
    ),
    OperationCommandSpec(
        kind="review",
        cli_args=("review",),
        reproduction_target="review",
        local_api_detach_supported=True,
    ),
    OperationCommandSpec(
        kind="optimize_case",
        cli_args=("optimize-case",),
        reproduction_target="optimize_case",
    ),
    OperationCommandSpec(
        kind="knowledge_post_action",
        cli_args=("knowledge-post-action",),
        reproduction_target="knowledge_post_action",
    ),
)
_OPERATION_COMMAND_SPECS_BY_KIND = {spec.kind: spec for spec in _OPERATION_COMMAND_SPECS}


def get_operation_command_spec(kind: OperationKind) -> OperationCommandSpec:
    try:
        return _OPERATION_COMMAND_SPECS_BY_KIND[kind]
    except KeyError as exc:
        raise ValueError(f"unsupported operation kind for command spec: {kind}") from exc


def build_operation_cli_argv(
    kind: OperationKind,
    *,
    request_file: Path,
    include_json: bool = True,
    include_detach: bool = False,
) -> list[str]:
    spec = get_operation_command_spec(kind)
    argv = [*spec.cli_args, "--request-file", str(request_file)]
    if include_json:
        argv.append("--json")
    if include_detach:
        argv.append("--detach")
    return argv


def build_operation_cli_command(kind: OperationKind, *, request_file: Path) -> str:
    return "munk " + " ".join(build_operation_cli_argv(kind, request_file=request_file))


def reproduction_target_kind_for_operation(kind: OperationKind) -> ReproductionTargetKind:
    spec = get_operation_command_spec(kind)
    if spec.reproduction_target is None:
        raise ValueError(f"unsupported reproduction target kind: {kind}")
    return spec.reproduction_target


def validate_local_api_detach_kind(kind: OperationKind) -> None:
    spec = get_operation_command_spec(kind)
    if not spec.local_api_detach_supported:
        raise ValueError(f"unsupported local api command: {kind}")
