#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
}

TEXT_BASENAMES = {
    "pyproject.toml",
    "uv.lock",
}

SKIP_DIR_NAMES = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".trae",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
    "runs",
    "tmp",
}


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str


PACKAGE_DIR_RENAMES: tuple[tuple[str, str], ...] = (
    ("packages/agents/plan-api", "packages/agents/plan-agent-api"),
    ("packages/agents/plan-runtime-local", "packages/agents/plan-agent-runtime-local"),
    ("packages/agents/runner-api", "packages/agents/runner-agent-api"),
    ("packages/agents/runner-runtime-local", "packages/agents/runner-agent-runtime-local"),
    ("packages/agents/judge-api", "packages/agents/judge-agent-api"),
    ("packages/agents/judge-runtime-local", "packages/agents/judge-agent-runtime-local"),
    ("packages/agents/review-api", "packages/agents/review-agent-api"),
    ("packages/agents/review-runtime-local", "packages/agents/review-agent-runtime-local"),
    ("packages/agents/recording-api", "packages/agents/recording-agent-api"),
    ("packages/agents/recording-runtime-local", "packages/agents/recording-agent-runtime-local"),
    ("packages/agents/knowledge-api", "packages/agents/knowledge-agent-api"),
    ("packages/agents/knowledge-runtime-local", "packages/agents/knowledge-agent-runtime-local"),
    ("packages/agents/optimize-api", "packages/agents/optimize-agent-api"),
    ("packages/agents/optimize-runtime-local", "packages/agents/optimize-agent-runtime-local"),
)

CONTENT_REPLACEMENTS: tuple[Replacement, ...] = (
    Replacement("munk-plan-local-runtime", "munk-plan-agent-runtime-local"),
    Replacement("munk-runner-local-runtime", "munk-runner-agent-runtime-local"),
    Replacement("munk-judge-local-runtime", "munk-judge-agent-runtime-local"),
    Replacement("munk-review-local-runtime", "munk-review-agent-runtime-local"),
    Replacement("munk-recording-local-runtime", "munk-recording-agent-runtime-local"),
    Replacement("munk-optimize-local-runtime", "munk-optimize-agent-runtime-local"),
    Replacement("munk-knowledge-agent-local-runtime", "munk-knowledge-agent-runtime-local"),
    Replacement("munk-plan-api", "munk-plan-agent-api"),
    Replacement("munk-runner-api", "munk-runner-agent-api"),
    Replacement("munk-judge-api", "munk-judge-agent-api"),
    Replacement("munk-review-api", "munk-review-agent-api"),
    Replacement("munk-recording-api", "munk-recording-agent-api"),
    Replacement("munk-optimize-api", "munk-optimize-agent-api"),
    Replacement("packages/agents/plan-runtime-local", "packages/agents/plan-agent-runtime-local"),
    Replacement("packages/agents/plan-api", "packages/agents/plan-agent-api"),
    Replacement("packages/agents/runner-runtime-local", "packages/agents/runner-agent-runtime-local"),
    Replacement("packages/agents/runner-api", "packages/agents/runner-agent-api"),
    Replacement("packages/agents/judge-runtime-local", "packages/agents/judge-agent-runtime-local"),
    Replacement("packages/agents/judge-api", "packages/agents/judge-agent-api"),
    Replacement("packages/agents/review-runtime-local", "packages/agents/review-agent-runtime-local"),
    Replacement("packages/agents/review-api", "packages/agents/review-agent-api"),
    Replacement("packages/agents/recording-runtime-local", "packages/agents/recording-agent-runtime-local"),
    Replacement("packages/agents/recording-api", "packages/agents/recording-agent-api"),
    Replacement("packages/agents/optimize-runtime-local", "packages/agents/optimize-agent-runtime-local"),
    Replacement("packages/agents/optimize-api", "packages/agents/optimize-agent-api"),
    Replacement("packages/agents/knowledge-runtime-local", "packages/agents/knowledge-agent-runtime-local"),
    Replacement("packages/agents/knowledge-api", "packages/agents/knowledge-agent-api"),
    Replacement("plan-api", "plan-agent-api"),
    Replacement("runner-api", "runner-agent-api"),
    Replacement("judge-api", "judge-agent-api"),
    Replacement("review-api", "review-agent-api"),
    Replacement("recording-api", "recording-agent-api"),
    Replacement("optimize-api", "optimize-agent-api"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename agent package directories and distribution names.")
    parser.add_argument("--root", type=Path, default=ROOT_DIR, help="Repository root")
    parser.add_argument("--apply", action="store_true", help="Apply changes instead of dry-run")
    parser.add_argument("--verbose", action="store_true", help="Print every changed file and rename")
    return parser.parse_args()


def should_skip_path(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    for index, part in enumerate(relative.parts):
        if part == "build" and index > 0 and relative.parts[0] == "config":
            continue
        if part in SKIP_DIR_NAMES or part.endswith(".egg-info"):
            return True
    return False


def is_text_file(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name in TEXT_BASENAMES


def ordered_replacements() -> tuple[Replacement, ...]:
    return tuple(sorted(CONTENT_REPLACEMENTS, key=lambda item: (-len(item.old), item.old)))


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if should_skip_path(root, path):
            continue
        if not is_text_file(path):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        files.append(path)
    return sorted(files)


def apply_replacements(text: str) -> tuple[str, dict[str, int]]:
    updated = text
    counts: dict[str, int] = {}
    for replacement in ordered_replacements():
        hit_count = updated.count(replacement.old)
        if hit_count == 0:
            continue
        updated = updated.replace(replacement.old, replacement.new)
        counts[replacement.old] = counts.get(replacement.old, 0) + hit_count
    return updated, counts


def collect_content_changes(root: Path) -> list[tuple[Path, dict[str, int]]]:
    changes: list[tuple[Path, dict[str, int]]] = []
    for path in iter_text_files(root):
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated, counts = apply_replacements(original)
        if updated == original:
            continue
        changes.append((path, counts))
    return changes


def write_content_changes(changes: list[tuple[Path, dict[str, int]]]) -> None:
    for path, _ in changes:
        original = path.read_text(encoding="utf-8")
        updated, _ = apply_replacements(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")


def collect_path_renames(root: Path) -> list[tuple[Path, Path]]:
    renames: list[tuple[Path, Path]] = []
    for old_rel, new_rel in PACKAGE_DIR_RENAMES:
        old_path = root / old_rel
        new_path = root / new_rel
        if old_path.exists():
            renames.append((old_path, new_path))
    return renames


def apply_path_renames(renames: list[tuple[Path, Path]]) -> None:
    for old_path, new_path in renames:
        if new_path.exists():
            raise FileExistsError(f"rename target already exists: {new_path}")
        old_path.rename(new_path)


def print_summary(
    *,
    root: Path,
    content_changes: list[tuple[Path, dict[str, int]]],
    path_renames: list[tuple[Path, Path]],
    verbose: bool,
) -> None:
    print(f"root: {root}")
    print(f"text files to update: {len(content_changes)}")
    print(f"directories to rename: {len(path_renames)}")
    if not verbose:
        return
    for path, counts in content_changes:
        details = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        print(f"content: {path.relative_to(root)} :: {details}")
    for old_path, new_path in path_renames:
        print(f"path: {old_path.relative_to(root)} -> {new_path.relative_to(root)}")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"root does not exist: {root}")

    content_changes = collect_content_changes(root)
    path_renames = collect_path_renames(root)
    print_summary(
        root=root,
        content_changes=content_changes,
        path_renames=path_renames,
        verbose=args.verbose,
    )

    if not args.apply:
        print("dry-run only; pass --apply to write changes")
        return 0

    write_content_changes(content_changes)
    apply_path_renames(path_renames)
    print("applied all content changes and directory renames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
