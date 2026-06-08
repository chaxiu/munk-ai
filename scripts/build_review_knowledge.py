from __future__ import annotations

import argparse
import json
from importlib import import_module


def main() -> None:
    parser = argparse.ArgumentParser()
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

    loader = KnowledgeSourceLoader()
    documents = loader.load_all()
    quality_report = loader.build_quality_report(documents=documents)
    payload = {
        "strict_quality": args.strict_quality,
        "quality_issue_count": quality_report.issue_count,
        "quality_issues": quality_report.to_list(limit=args.quality_report_limit),
    }

    if args.strict_quality and quality_report.issue_count:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    result = ReviewKnowledgeBuildService(loader=loader).build()
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
