from __future__ import annotations

import argparse
import json
import shutil
from importlib import import_module
from pathlib import Path


def _clean_build_root(build_root: Path) -> None:
    if build_root.exists():
        shutil.rmtree(build_root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root",
        type=Path,
        default=None,
        help="review knowledge source root; defaults to the runtime package resource path",
    )
    parser.add_argument(
        "--build-root",
        type=Path,
        default=None,
        help="review knowledge build root for sqlite output; defaults to the runtime package default",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove the existing review sqlite build root before rebuilding",
    )
    parser.add_argument(
        "--strict-quality",
        action="store_true",
        help="fail before build when the review knowledge source has quality issues",
    )
    parser.add_argument(
        "--quality-report-limit",
        type=int,
        default=20,
        help="maximum number of quality issues to include in the JSON output",
    )
    args = parser.parse_args()
    try:
        build_module = import_module("munk_review_local.knowledge_build_service")
        source_module = import_module("munk_review_local.knowledge_source")
    except ImportError as exc:  # pragma: no cover - depends on local install layout
        raise SystemExit(
            "review local runtime is not installed; install review-runtime-local before "
            "building review knowledge"
        ) from exc

    ReviewKnowledgeBuildService = build_module.ReviewKnowledgeBuildService
    KnowledgeSourceLoader = source_module.KnowledgeSourceLoader

    source_root = args.source_root.resolve() if args.source_root is not None else None
    build_root = args.build_root.resolve() if args.build_root is not None else None
    loader = KnowledgeSourceLoader(root_dir=source_root)
    build_service = ReviewKnowledgeBuildService(
        root_dir=source_root,
        build_root=build_root,
        loader=loader,
    )
    if args.clean:
        _clean_build_root(build_service.build_root)
    documents = loader.load_all()
    quality_report = loader.build_quality_report(documents=documents)
    payload: dict[str, object] = {
        "source_root": str(loader.root_dir),
        "build_root": str(build_service.build_root),
        "clean": args.clean,
        "strict_quality": args.strict_quality,
        "quality_issue_count": quality_report.issue_count,
        "quality_issues": quality_report.to_list(limit=args.quality_report_limit),
    }

    if args.strict_quality and quality_report.issue_count:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    result = build_service.build()
    print(
        json.dumps(
            {
                **payload,
                "db_path": str(result.db_path),
                "build_manifest_path": str(result.build_manifest_path),
                "total_cases": result.total_cases,
                "rebuilt_cases": result.rebuilt_cases,
                "skipped_cases": result.skipped_cases,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
