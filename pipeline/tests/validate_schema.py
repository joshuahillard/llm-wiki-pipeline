"""
validate_schema.py — Validate a JSON result against validation_result.schema.json.

Standalone CLI utility for the golden corpus harness. Validates that
validator_runner.py output conforms to the expected schema before
any assertion logic runs.

All schema operations are delegated to schema_helpers.py.  This file
owns only the CLI interface and sys.exit() semantics.

Usage:
    python validate_schema.py --file result.json
    cat result.json | python validate_schema.py --stdin

Exit codes:
    0 — Valid
    1 — Schema violation(s) found
    2 — Configuration error (missing schema, bad JSON, missing dependency)
"""

import argparse
import json
import sys
from pathlib import Path

from schema_helpers import SchemaError, load_schema, validate


def load_result(args):
    """Load the JSON result from --file or --stdin. Exactly one must be set."""
    if args.file:
        p = Path(args.file)
        if not p.exists():
            print(f"ERROR: File not found: {p}", file=sys.stderr)
            sys.exit(2)
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"ERROR: File is not valid JSON: {e}", file=sys.stderr)
            sys.exit(2)

    # --stdin
    raw = sys.stdin.read()
    if not raw.strip():
        print("ERROR: Empty input on stdin", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: Stdin is not valid JSON: {e}", file=sys.stderr)
        sys.exit(2)


def main():
    parser = argparse.ArgumentParser(
        description="Validate a JSON result against "
                    "validation_result.schema.json"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file", type=str,
        help="Path to a JSON file to validate",
    )
    group.add_argument(
        "--stdin", action="store_true",
        help="Read JSON from stdin",
    )
    args = parser.parse_args()

    try:
        schema = load_schema()
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    result = load_result(args)

    try:
        errors = validate(result, schema)
    except SchemaError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    if not errors:
        print("VALID: Result conforms to validation_result.schema.json")
        sys.exit(0)

    print(
        f"INVALID: {len(errors)} schema violation(s) found:\n",
        file=sys.stderr,
    )
    for path_str, message in errors:
        print(f"  [{path_str}] {message}", file=sys.stderr)

    sys.exit(1)


if __name__ == "__main__":
    main()
