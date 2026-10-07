#!/usr/bin/env python3
"""Count repository code lines for selected file types.

The script relies on ``git ls-files --cached --others --exclude-standard`` so
ignored files and directories from ``.gitignore`` are excluded automatically.
By default it counts Python and Vue source files.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_EXTENSIONS = ("py", "vue", "ts", "css")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "统计仓库代码行数，默认涵盖 Python 和 Vue，并自动排除 .gitignore 中的文件。"
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Git 仓库根目录，默认自动定位到当前脚本所在仓库。",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(DEFAULT_EXTENSIONS),
        help="需要统计的扩展名列表，例如: py vue ts。",
    )
    return parser.parse_args()


def list_git_files(repo_root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("未找到 git 命令，请先安装 Git。") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"执行 git ls-files 失败: {stderr or exc}") from exc

    entries = [item for item in result.stdout.split(b"\0") if item]
    return [repo_root / Path(item.decode("utf-8", errors="surrogateescape")) for item in entries]


def count_file_lines(file_path: Path) -> int:
    with file_path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def main() -> int:
    args = parse_args()
    repo_root = args.root.resolve()
    extensions = {ext.lower().lstrip(".") for ext in args.extensions if ext.strip()}

    if not extensions:
        print("未提供有效的扩展名。", file=sys.stderr)
        return 1

    if not (repo_root / ".git").exists():
        print(f"目录不是 Git 仓库: {repo_root}", file=sys.stderr)
        return 1

    totals_by_extension: dict[str, int] = defaultdict(int)
    files_by_extension: dict[str, int] = defaultdict(int)

    for file_path in list_git_files(repo_root):
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower().lstrip(".")
        if suffix not in extensions:
            continue

        line_count = count_file_lines(file_path)
        totals_by_extension[suffix] += line_count
        files_by_extension[suffix] += 1

    total_files = sum(files_by_extension.values())
    total_lines = sum(totals_by_extension.values())

    print(f"仓库: {repo_root}")
    print(f"统计扩展名: {', '.join(sorted(extensions))}")
    print()
    print(f"{'类型':<10}{'文件数':>10}{'总行数':>12}")
    print("-" * 32)

    for extension in sorted(extensions):
        print(
            f".{extension:<9}{files_by_extension[extension]:>10}{totals_by_extension[extension]:>12}"
        )

    print("-" * 32)
    print(f"{'TOTAL':<10}{total_files:>10}{total_lines:>12}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
