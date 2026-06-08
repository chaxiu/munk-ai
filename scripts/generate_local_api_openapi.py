from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from munk.adapters.local_api.app import create_local_api_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "apps" / "web-ui" / "openapi" / "local-api.json"


def _serialize_openapi() -> str:
    app = create_local_api_app(start_recording_bridge=False)
    schema = app.openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _write_schema(output_path: Path, content: str) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


def _check_schema(output_path: Path, content: str) -> int:
    if not output_path.exists():
        print(f"missing generated schema: {output_path}", file=sys.stderr)
        return 1
    current = output_path.read_text(encoding="utf-8")
    if current != content:
        print(f"outdated generated schema: {output_path}", file=sys.stderr)
        return 1
    print(f"schema is up to date: {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Local API OpenAPI schema for web-ui.")
    parser.add_argument("mode", choices=("write", "check"))
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to the generated OpenAPI JSON file.",
    )
    args = parser.parse_args()

    content = _serialize_openapi()
    if args.mode == "write":
        return _write_schema(args.output, content)
    return _check_schema(args.output, content)


if __name__ == "__main__":
    raise SystemExit(main())
