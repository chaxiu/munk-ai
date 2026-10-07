#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".c",
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mts",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".yaml",
    ".yml",
}

TEXT_BASENAMES = {
    ".gitignore",
    "Dockerfile",
    "pyproject.toml",
    "README",
    "README.md",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "uv.lock",
}

SKIP_DIR_NAMES = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".review-runtime-local",
    ".ruff_cache",
    ".tmp",
    ".tox",
    ".vscode",
    "__pycache__",
    "android-adb",
    "apk",
    "build",
    "development-log",
    "dist",
    "llamacpp",
    "node_modules",
    "runs",
    "screen_shot",
    "tmp",
    ".trae",
}

SKIP_RELATIVE_PREFIXES = {
    ("code", "Todo"),
}


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str
    risk: str
    apply_to_path: bool = True
    apply_to_content: bool = True


REPLACEMENTS: tuple[Replacement, ...] = (
    # Low risk: docs, branding, CLI help, visible strings.
    Replacement("MonkeyAI Home", "Munk AI Home", "low", apply_to_path=False),
    Replacement("MonkeyAI home", "Munk AI home", "low", apply_to_path=False),
    Replacement("Monkey-AI", "Munk AI", "low", apply_to_path=False),
    Replacement("Monkey AI", "Munk AI", "low", apply_to_path=False),
    Replacement("MonkeyAI", "MunkAI", "low"),
    Replacement("ai-monkey-workspace", "munk-workspace", "low"),
    Replacement("ai-monkey-tech", "munk-tech", "low"),
    Replacement("monkey-ai", "munk", "low"),
    # Medium risk: env vars, workspace config dir, user data dir.
    Replacement(".aimonkey", ".munk", "medium"),
    Replacement("AIMONKEY_", "MUNK_", "medium"),
    Replacement("monkeyai", "munkai", "medium"),
    # High risk: package names, import paths, entry points, cross-package deps.
    Replacement("Aimonkey", "Munk", "high"),
    Replacement("aimonkey", "munk", "high"),
)


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass
class ContentChange:
    path: Path
    replacement_counts: dict[str, int]


@dataclass
class PathRename:
    path: Path
    new_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rename Monkey AI branding and internal identifiers to Munk. "
            "Defaults to dry-run; pass --apply to write changes."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT_DIR,
        help="Repository root to operate on. Defaults to the current project root.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write file contents and perform path renames. Default mode is dry-run.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every planned or applied content/path change.",
    )
    return parser.parse_args()


def ordered_replacements(*, for_path: bool) -> list[Replacement]:
    candidates = [
        replacement
        for replacement in REPLACEMENTS
        if (replacement.apply_to_path if for_path else replacement.apply_to_content)
    ]
    return sorted(candidates, key=lambda item: (-len(item.old), RISK_ORDER[item.risk], item.old))


def should_skip_path(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    parts = relative.parts
    for prefix in SKIP_RELATIVE_PREFIXES:
        if parts[: len(prefix)] == prefix:
            return True
    for part in parts:
        if part in SKIP_DIR_NAMES:
            return True
        if part.startswith(".venv"):
            return True
        if part.endswith(".egg-info"):
            return True
    return False


def should_process_text_file(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES or path.name in TEXT_BASENAMES


def iter_candidate_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if should_skip_path(root, path):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if should_process_text_file(path):
            yield path


def apply_replacements(text: str, replacements: Iterable[Replacement]) -> tuple[str, dict[str, int]]:
    updated = text
    counts: dict[str, int] = {}
    for replacement in replacements:
        match_count = updated.count(replacement.old)
        if match_count == 0:
            continue
        updated = updated.replace(replacement.old, replacement.new)
        counts[replacement.old] = counts.get(replacement.old, 0) + match_count
    return updated, counts


def collect_content_changes(root: Path) -> list[ContentChange]:
    replacements = ordered_replacements(for_path=False)
    changes: list[ContentChange] = []
    for path in iter_candidate_files(root):
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated, counts = apply_replacements(original, replacements)
        if updated == original:
            continue
        changes.append(ContentChange(path=path, replacement_counts=counts))
    return changes


def write_content_changes(changes: Iterable[ContentChange]) -> None:
    replacements = ordered_replacements(for_path=False)
    for change in changes:
        original = change.path.read_text(encoding="utf-8")
        updated, _ = apply_replacements(original, replacements)
        if updated != original:
            change.path.write_text(updated, encoding="utf-8")


def renamed_path(path: Path) -> Path:
    replacements = ordered_replacements(for_path=True)
    current = path
    for replacement in replacements:
        if replacement.old not in current.name:
            continue
        current = current.with_name(current.name.replace(replacement.old, replacement.new))
    return current


def collect_path_renames(root: Path) -> list[PathRename]:
    candidates: list[PathRename] = []
    for path in sorted(root.rglob("*"), key=lambda item: (len(item.parts), str(item)), reverse=True):
        if should_skip_path(root, path):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        new_path = renamed_path(path)
        if new_path != path:
            candidates.append(PathRename(path=path, new_path=new_path))
    return candidates


def apply_path_renames(renames: Iterable[PathRename]) -> None:
    for rename in renames:
        if not rename.path.exists():
            continue
        if rename.new_path.exists():
            raise FileExistsError(
                f"cannot rename {rename.path} -> {rename.new_path}: target already exists"
            )
        rename.path.rename(rename.new_path)


def print_mapping_summary() -> None:
    grouped: dict[str, list[Replacement]] = defaultdict(list)
    for replacement in REPLACEMENTS:
        grouped[replacement.risk].append(replacement)
    print("Replacement map:")
    for risk in ("low", "medium", "high"):
        print(f"  {risk}:")
        for replacement in grouped[risk]:
            print(f"    {replacement.old!r} -> {replacement.new!r}")


def print_change_summary(
    *,
    root: Path,
    content_changes: list[ContentChange],
    path_renames: list[PathRename],
    verbose: bool,
) -> None:
    replacement_counter: Counter[str] = Counter()
    for change in content_changes:
        replacement_counter.update(change.replacement_counts)

    print(f"Repository root: {root}")
    print(f"Planned content changes: {len(content_changes)} files")
    if replacement_counter:
        print("Replacement hit counts:")
        for old, count in replacement_counter.most_common():
            replacement = next(item for item in REPLACEMENTS if item.old == old)
            print(f"  [{replacement.risk}] {old!r}: {count}")
    print(f"Planned path renames: {len(path_renames)} paths")

    if not verbose:
        return

    if content_changes:
        print("Content changes:")
        for change in content_changes:
            relative = change.path.relative_to(root)
            counts = ", ".join(f"{key!r}={value}" for key, value in sorted(change.replacement_counts.items()))
            print(f"  {relative}: {counts}")

    if path_renames:
        print("Path renames:")
        for rename in path_renames:
            print(f"  {rename.path.relative_to(root)} -> {rename.new_path.relative_to(root)}")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"repository root does not exist: {root}")

    print_mapping_summary()
    content_changes = collect_content_changes(root)
    path_renames = collect_path_renames(root)
    print_change_summary(
        root=root,
        content_changes=content_changes,
        path_renames=path_renames,
        verbose=args.verbose,
    )

    if not args.apply:
        print("Dry-run only. Re-run with --apply to write changes.")
        return 0

    write_content_changes(content_changes)
    apply_path_renames(path_renames)
    print("Applied all content changes and path renames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
