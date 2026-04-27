"""
Backward-compatible test wrapper for pipeline/schema_helpers.py.
"""

import importlib.util
from pathlib import Path


PRODUCTION_PATH = Path(__file__).resolve().parent.parent / "schema_helpers.py"
SPEC = importlib.util.spec_from_file_location(
    "_pipeline_schema_helpers_wrapper",
    str(PRODUCTION_PATH),
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SchemaError = MODULE.SchemaError
load_schema = MODULE.load_schema
validate = MODULE.validate
