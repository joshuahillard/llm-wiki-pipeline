"""
Backward-compatible test wrapper for pipeline/validator_runner.py.
"""

import importlib.util
from pathlib import Path


PRODUCTION_PATH = Path(__file__).resolve().parent.parent / "validator_runner.py"
SPEC = importlib.util.spec_from_file_location(
    "_pipeline_validator_runner_wrapper",
    str(PRODUCTION_PATH),
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SchemaError = MODULE.SchemaError
ValidatorError = MODULE.ValidatorError
ConfigError = MODULE.ConfigError
ParserError = MODULE.ParserError
ProviderError = MODULE.ProviderError
EXIT_APPROVE = MODULE.EXIT_APPROVE
EXIT_REJECT = MODULE.EXIT_REJECT
EXIT_ESCALATE = MODULE.EXIT_ESCALATE
EXIT_SCHEMA_FAULT = MODULE.EXIT_SCHEMA_FAULT
EXIT_SYSTEM_FAULT = MODULE.EXIT_SYSTEM_FAULT
EXIT_TOKEN_OVERFLOW = MODULE.EXIT_TOKEN_OVERFLOW
default_provider = MODULE.default_provider
load_config = MODULE.load_config
load_text_file = MODULE.load_text_file
run_parser = MODULE.run_parser
estimate_tokens_by_bytes = MODULE.estimate_tokens_by_bytes
count_tokens_for_provider = MODULE.count_tokens_for_provider
check_token_budget = MODULE.check_token_budget
build_llm_payload = MODULE.build_llm_payload
parse_llm_response = MODULE.parse_llm_response
run = MODULE.run
main = MODULE.main


if __name__ == "__main__":
    main()
