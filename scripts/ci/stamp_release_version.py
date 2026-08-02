#!/usr/bin/env python3
"""Stamp pyproject.toml version from a git tag and resolve the release channel.

Tag is the release-version authority for CI builds. This script rewrites only the
local working tree (never commits) so assemble/publish read the tagged version.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR / "src") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "src"))

from munk.runtime_distribution.release_publish_config import (  # noqa: E402
    PROJECT_VERSION_PATTERN,
    is_non_final_version,
    load_release_version,
)

VERSION_LINE_PATTERN = re.compile(
    r'^(\s*version\s*=\s*")([^"]+)("\s*)$',
    re.MULTILINE,
)


def parse_release_tag(tag: str) -> str:
    raw = tag.strip()
    if not raw:
        raise RuntimeError("release tag must not be empty")
    if raw.startswith(("v", "V")) and len(raw) > 1 and raw[1].isdigit():
        raw = raw[1:]
    if not raw or not raw[0].isdigit():
        raise RuntimeError(
            f"unsupported release tag {tag!r}; expected v-prefixed PEP440 version such as v0.33.0 or v0.33.0b1"
        )
    return raw


def resolve_channel_for_version(version: str) -> str:
    return "beta" if is_non_final_version(version) else "stable"


def stamp_project_version(*, project_root: Path, version: str) -> str:
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise RuntimeError(f"missing pyproject.toml: {pyproject_path}")

    original = pyproject_path.read_text(encoding="utf-8")
    in_project_section = False
    replaced = False
    output_lines: list[str] = []
    for raw_line in original.splitlines(keepends=True):
        stripped = raw_line.strip()
        if stripped.startswith("["):
            in_project_section = stripped == "[project]"
            output_lines.append(raw_line)
            continue
        if in_project_section and PROJECT_VERSION_PATTERN.match(raw_line.rstrip("\n")):
            match = VERSION_LINE_PATTERN.match(raw_line.rstrip("\n"))
            if match is None:
                raise RuntimeError(f"unable to rewrite version line in {pyproject_path}: {raw_line!r}")
            newline = "\n" if raw_line.endswith("\n") else ""
            output_lines.append(f"{match.group(1)}{version}{match.group(3)}{newline}")
            replaced = True
            in_project_section = False
            continue
        output_lines.append(raw_line)

    if not replaced:
        raise RuntimeError(f"missing [project].version in {pyproject_path}")

    pyproject_path.write_text("".join(output_lines), encoding="utf-8")
    stamped = load_release_version(project_root)
    if stamped != version:
        raise RuntimeError(f"stamped version mismatch: expected {version!r}, got {stamped!r}")
    return stamped


def _append_github_output(*, path: Path, values: dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in values.items()]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tag", help="Git tag such as v0.33.0 or v0.33.0b1")
    source.add_argument(
        "--from-pyproject",
        action="store_true",
        help="Read version from pyproject.toml without rewriting it",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=ROOT_DIR,
        help="Repository root containing pyproject.toml",
    )
    parser.add_argument(
        "--github-output",
        type=Path,
        default=None,
        help="Optional GitHub Actions output file (usually $GITHUB_OUTPUT)",
    )
    args = parser.parse_args(argv)

    project_root = args.project_root.resolve()
    if args.from_pyproject:
        version = load_release_version(project_root)
    else:
        version = parse_release_tag(args.tag)
        stamp_project_version(project_root=project_root, version=version)

    channel = resolve_channel_for_version(version)
    print(f"version={version}")
    print(f"channel={channel}")

    if args.github_output is not None:
        _append_github_output(
            path=args.github_output,
            values={"version": version, "channel": channel},
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
