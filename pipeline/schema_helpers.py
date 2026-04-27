"""
schema_helpers.py — Shared schema loading and validation for LLM-Wiki pipeline.

This is the production location for validation_result.schema.json operations.
Test-side modules may wrap this file for backward compatibility, but this
module is the intended single source of truth for schema loading and
validation behavior.
"""

import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR / "validation_result.schema.json"


class SchemaError(Exception):
    """Schema loading or validation failure."""
    pass


def load_schema(schema_path=None):
    """Load and structurally validate validation_result.schema.json."""
    path = Path(schema_path) if schema_path else SCHEMA_PATH
    if not path.exists():
        raise SchemaError(f"Schema not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            schema = json.load(f)
    except (json.JSONDecodeError, ValueError) as exc:
        raise SchemaError(f"Schema is not valid JSON: {exc}") from exc

    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:
        raise SchemaError(
            "jsonschema is required. Install with: pip install jsonschema"
        ) from exc

    try:
        Draft7Validator.check_schema(schema)
    except Exception as exc:
        raise SchemaError(
            f"Schema itself is structurally invalid: {exc}"
        ) from exc

    return schema


def validate(result_dict, schema):
    """Validate result against schema and return sorted path/message pairs."""
    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:
        raise SchemaError(
            "jsonschema is required. Install with: pip install jsonschema"
        ) from exc

    validator = Draft7Validator(schema)
    errors = []
    for error in validator.iter_errors(result_dict):
        path_str = (
            " → ".join(str(p) for p in error.absolute_path) or "(root)"
        )
        errors.append((path_str, error.message))
    errors.sort(key=lambda e: e[0])
    return errors
