"""
run_harness.py — Golden corpus test harness for LLM-Wiki pipeline.

Executes fixtures from corpus_manifest.json against pipeline components
and reports pass/fail for each expected outcome.

Usage:
    python run_harness.py [--stage parser|validator|all] [--fixture ID]

Exit codes:
    0 — All executed assertions passed AND all requested stages have
        assertions implemented. Only possible when every stage in scope
        has a real test runner.
    1 — One or more assertions failed. This includes parser pre-check
        failures for validator-stage fixtures, because a broken parser
        is a real failure, not partial coverage.
    2 — Harness configuration error: missing files, invalid manifest,
        missing jsonschema dependency, unknown fixture ID.
    3 — All executed assertions passed, but one or more requested stages
        have no assertion runner implemented yet. This is distinct from
        exit 1: the work that *was* tested is green, but the harness
        cannot claim full coverage.

Stage semantics:
    --stage parser    Run parser assertions on ALL fixtures (parser,
                      validator, and integration). Every fixture file
                      must be parseable; manifest stage does not exclude
                      a fixture from parser checks.
    --stage validator Run parser assertions on validator fixtures (as a
                      pre-check), then run validator assertions using
                      deterministic canned responses from
                      golden_corpus/responses/.
    --stage all       Run parser assertions on all fixtures, then
                      validator assertions, then integration assertions.

File layout assumption:
    pipeline/
        parse_identity.py          <-- PARSER_PATH
        tests/
            run_harness.py         <-- this file
            golden_corpus/
                corpus_manifest.json
                golden_corpus_manifest.schema.json
                approve/
                reject/
                escalate/
                adversarial/
                integration/
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CORPUS_DIR = SCRIPT_DIR / "golden_corpus"
MANIFEST_PATH = CORPUS_DIR / "corpus_manifest.json"
SCHEMA_PATH = CORPUS_DIR / "golden_corpus_manifest.schema.json"
PARSER_PATH = SCRIPT_DIR.parent / "parse_identity.py"

PARSER_TIMEOUT_SECONDS = 30

# ---------------------------------------------------------------------------
# Validator stage constants
# ---------------------------------------------------------------------------
VALIDATOR_RUNNER_PATH = SCRIPT_DIR.parent / "validator_runner.py"
RESPONSES_DIR = CORPUS_DIR / "responses"

# Frozen config for golden corpus runs.  Validator-stage tests use this
# instead of ambient ops/validator_config.json so that local config edits
# cannot change corpus outcomes.
HARNESS_VALIDATOR_CONFIG = {
    "provider": "harness",
    "model_id": "harness-stub",
    "temperature": 0.0,
    "top_p": 1.0,
    "max_context_tokens": 128000,
    "tokenizer_id": "harness-stub",
}

# Frozen system prompt and taxonomy for golden corpus runs.  These are
# empty strings so that token budget calculations are deterministic and
# payload shape cannot drift from local file edits.  The canned responses
# already encode the "correct" LLM behavior for each fixture — the prompt
# and taxonomy that produced them are baked into the response files.
HARNESS_SYSTEM_PROMPT = ""
HARNESS_TAXONOMY = ""

# Exit codes that never reach the provider.  Fixtures expecting these
# codes do not need canned response files.
_NO_PROVIDER_EXIT_CODES = frozenset({
    4,   # SYSTEM_FAULT — parser fails before provider is called
    5,   # TOKEN_OVERFLOW — budget check rejects before provider is called
})


class TestResult:
    def __init__(self, fixture_id, stage, passed, message, expected, actual):
        self.fixture_id = fixture_id
        self.stage = stage
        self.passed = passed
        self.message = message
        self.expected = expected
        self.actual = actual


def load_manifest():
    if not MANIFEST_PATH.exists():
        print(f"ERROR: Manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(2)

    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema not found: {SCHEMA_PATH}", file=sys.stderr)
        sys.exit(2)

    try:
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: Manifest is not valid JSON: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        with open(SCHEMA_PATH) as f:
            schema = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"ERROR: Schema is not valid JSON: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        from jsonschema import validate, ValidationError
    except ImportError:
        print("ERROR: jsonschema is required. "
              "Install with: pip install jsonschema", file=sys.stderr)
        sys.exit(2)

    try:
        validate(instance=manifest, schema=schema)
    except ValidationError as e:
        print(f"ERROR: Manifest fails schema validation: {e.message}",
              file=sys.stderr)
        sys.exit(2)

    return manifest


def check_prerequisites():
    if not PARSER_PATH.exists():
        print(f"ERROR: parse_identity.py not found: {PARSER_PATH}",
              file=sys.stderr)
        sys.exit(2)


def resolve_fixture_path(fixture):
    return CORPUS_DIR / fixture["path"]


def run_parser_test(fixture):
    """Run parse_identity.py against a fixture and verify parser expectations.

    This function runs for every fixture regardless of manifest stage:
    - Parser-stage fixtures: the parser IS the test.
    - Validator-stage fixtures: the parser is a pre-check.
    - Integration-stage fixtures: the parser is a pre-check.

    Returns a list of TestResult (one per assertion).
    """
    results = []
    fpath = resolve_fixture_path(fixture)
    fid = fixture["id"]

    if not fpath.exists():
        results.append(TestResult(
            fid, "parser", False,
            f"Fixture file not found: {fpath}",
            "file exists", "missing"
        ))
        return results

    try:
        proc = subprocess.run(
            [sys.executable, str(PARSER_PATH), str(fpath)],
            capture_output=True, text=True,
            timeout=PARSER_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        results.append(TestResult(
            fid, "parser", False,
            f"Parser timed out after {PARSER_TIMEOUT_SECONDS}s",
            f"completes within {PARSER_TIMEOUT_SECONDS}s", "timeout"
        ))
        return results
    except FileNotFoundError as e:
        results.append(TestResult(
            fid, "parser", False,
            f"Failed to execute parser: {e}",
            "parser executable found", str(e)
        ))
        return results
    except Exception as e:
        results.append(TestResult(
            fid, "parser", False,
            f"Unexpected error running parser: {type(e).__name__}: {e}",
            "parser runs without error", str(e)
        ))
        return results

    actual_exit = proc.returncode

    try:
        actual_output = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        results.append(TestResult(
            fid, "parser", False,
            f"Parser stdout is not valid JSON: {proc.stdout[:200]}",
            "valid JSON on stdout", "invalid JSON"
        ))
        return results

    expected_parser = fixture["expected_parser"]

    if expected_parser == "error":
        expected_exit = fixture["expected_exit_code"]
        if actual_exit != expected_exit:
            results.append(TestResult(
                fid, "parser", False,
                f"Expected exit {expected_exit}, got exit {actual_exit}",
                expected_exit, actual_exit
            ))
        else:
            results.append(TestResult(
                fid, "parser", True,
                f"Exit code {actual_exit} matches expected",
                expected_exit, actual_exit
            ))

        if actual_output.get("frontmatter_valid") is not False:
            results.append(TestResult(
                fid, "parser", False,
                f"Expected frontmatter_valid=false, "
                f"got {actual_output.get('frontmatter_valid')}",
                False, actual_output.get("frontmatter_valid")
            ))

        expected_error = fixture.get("expected_parser_error")
        if expected_error:
            actual_error = actual_output.get("error", "")
            if expected_error in actual_error:
                results.append(TestResult(
                    fid, "parser", True,
                    f"Error contains '{expected_error}'",
                    expected_error, actual_error
                ))
            else:
                results.append(TestResult(
                    fid, "parser", False,
                    f"Error does not contain '{expected_error}'",
                    expected_error, actual_error
                ))

    elif expected_parser == "success":
        if actual_exit != 0:
            results.append(TestResult(
                fid, "parser", False,
                f"Expected parser success (exit 0), got exit {actual_exit}",
                0, actual_exit
            ))
        else:
            results.append(TestResult(
                fid, "parser", True,
                "Parser returned exit 0 as expected",
                0, 0
            ))

        if actual_output.get("frontmatter_valid") is not True:
            results.append(TestResult(
                fid, "parser", False,
                f"Expected frontmatter_valid=true, "
                f"got {actual_output.get('frontmatter_valid')}",
                True, actual_output.get("frontmatter_valid")
            ))

        if not actual_output.get("source_id"):
            results.append(TestResult(
                fid, "parser", False,
                "Expected source_id to be non-null",
                "non-null", actual_output.get("source_id")
            ))

    else:
        results.append(TestResult(
            fid, "parser", False,
            f"Unknown expected_parser value: '{expected_parser}'",
            "success or error", expected_parser
        ))

    return results


def collect_parser_eligible(fixtures, stage):
    """Collect fixtures eligible for parser assertions, deduplicated by ID.

    Parser assertions run on every fixture that has a file to parse.
    The stage flag determines scope:
    - parser:    all fixtures (parser + validator + integration)
    - validator: validator fixtures only
    - all:       all fixtures (parser + validator + integration)

    Returns fixtures in manifest order, deduplicated by ID.
    """
    if stage in ("parser", "all"):
        eligible = fixtures
    elif stage == "validator":
        eligible = [f for f in fixtures if f["stage"] == "validator"]
    else:
        eligible = []

    seen = set()
    result = []
    for f in eligible:
        if f["id"] not in seen:
            seen.add(f["id"])
            result.append(f)
    return result


def print_results(results, verbose=False):
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    if verbose:
        for r in results:
            mark = "PASS" if r.passed else "FAIL"
            print(f"  [{mark}] {r.fixture_id}: {r.message}")

    print(f"\n{'='*60}")
    print(f"Results: {len(passed)} passed, {len(failed)} failed, "
          f"{len(results)} total")

    if failed:
        print(f"\nFailed assertions:")
        for r in failed:
            print(f"  {r.fixture_id}: {r.message}")
            print(f"    expected: {r.expected}")
            print(f"    actual:   {r.actual}")

    return len(failed) == 0


# ---------------------------------------------------------------------------
# Validator stage helpers
# ---------------------------------------------------------------------------
def _response_mode(fixture):
    """Return the response_mode for a fixture.

    Manifest field:
        response_mode = "valid"       -> canned response must satisfy schema
        response_mode = "invalid_raw" -> canned response is intentionally bad
                                         (for SCHEMA_FAULT testing)
    Default is 'valid'.
    """
    return fixture.get("response_mode", "valid")


def _load_validator_runner():
    """Lazy-import the production validator_runner.py.

    Returns the module on success.
    Exits 2 on any import failure — a broken validator_runner is a harness
    configuration error, not partial coverage.
    """
    if not VALIDATOR_RUNNER_PATH.exists():
        print(f"ERROR: validator_runner.py not found: "
              f"{VALIDATOR_RUNNER_PATH}", file=sys.stderr)
        sys.exit(2)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "validator_runner", str(VALIDATOR_RUNNER_PATH)
    )
    vr = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(vr)
    except SystemExit as exc:
        print(f"ERROR: validator_runner.py called sys.exit({exc.code}) "
              f"during import (missing dependency?)", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print(f"ERROR: validator_runner.py failed to import: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)

    return vr


def _load_corpus_responses(manifest_fixtures):
    """Load and validate canned LLM responses from golden_corpus/responses/.

    Each file is named {fixture_id}.json and must be a valid JSON document.
    Files with response_mode="valid" are eagerly validated against
    validation_result.schema.json.  Files with response_mode="invalid_raw"
    are stored as-is (they are intentionally malformed for SCHEMA_FAULT
    testing).

    Returns dict mapping fixture_id -> {"raw": str, "response_mode": str}.
    Exits 2 if responses/ is missing, a required fixture has no response
    file, or any "valid" response file fails schema validation.
    """
    if not RESPONSES_DIR.exists():
        print(f"ERROR: Canned responses directory not found: "
              f"{RESPONSES_DIR}", file=sys.stderr)
        sys.exit(2)

    # Import schema_helpers lazily so --stage parser works even if
    # schema_helpers.py is broken.
    try:
        from schema_helpers import (
            SchemaError, load_schema, validate as schema_validate,
        )
    except Exception as exc:
        print(f"ERROR: schema_helpers.py failed to import: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)

    # Load the schema once for validating all "valid" response files.
    try:
        result_schema = load_schema()
    except Exception as exc:
        print(f"ERROR: Failed to load validation schema: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)

    # Determine which fixture IDs require canned responses.
    # Fixtures whose expected_exit_code is in _NO_PROVIDER_EXIT_CODES
    # never reach the provider, so they do not need a response file.
    fixture_by_id = {
        f["id"]: f
        for f in manifest_fixtures
        if f["stage"] == "validator"
        and f["expected_exit_code"] not in _NO_PROVIDER_EXIT_CODES
    }

    responses = {}
    errors = []

    for fid, fixture in sorted(fixture_by_id.items()):
        resp_file = RESPONSES_DIR / f"{fid}.json"
        mode = _response_mode(fixture)

        if not resp_file.exists():
            errors.append(f"Missing response file: {resp_file}")
            continue

        try:
            with open(resp_file, encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            errors.append(f"Cannot read {resp_file}: {exc}")
            continue

        # For intentionally invalid raw responses, store as-is and
        # skip eager schema validation.
        if mode == "invalid_raw":
            responses[fid] = {"raw": raw, "response_mode": mode}
            continue

        # Otherwise require parseable JSON + schema-valid content.
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid JSON in {resp_file}: {exc}")
            continue

        try:
            s_errors = schema_validate(data, result_schema)
        except SchemaError as exc:
            errors.append(
                f"Schema validation infrastructure failed for "
                f"{resp_file}: {exc}"
            )
            continue

        if s_errors:
            preview = "; ".join(f"[{p}] {m}" for p, m in s_errors[:3])
            suffix = (
                f" (and {len(s_errors) - 3} more)"
                if len(s_errors) > 3 else ""
            )
            errors.append(
                f"Schema violations in {resp_file}: {preview}{suffix}"
            )
            continue

        responses[fid] = {"raw": raw, "response_mode": mode}

    if errors:
        print("ERROR: Canned response validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        sys.exit(2)

    return responses


def _build_corpus_provider(corpus_responses, fixture_id):
    """Return a provider callable for a single fixture.

    The provider is keyed by fixture_id, not by source_id, so two
    fixtures sharing a source_id get distinct deterministic responses.
    The config argument is ignored — corpus runs are fully hermetic.
    """
    def corpus_provider(payload, config):
        if fixture_id not in corpus_responses:
            raise ValueError(
                f"No canned response for fixture '{fixture_id}'. "
                f"Available: {sorted(corpus_responses.keys())}"
            )
        return corpus_responses[fixture_id]["raw"]
    return corpus_provider


def run_validator_test(fixture, vr_module, corpus_responses):
    """Run validator_runner against a fixture and verify expectations.

    Args:
        fixture:           Fixture dict from corpus_manifest.json.
        vr_module:         Imported validator_runner module.
        corpus_responses:  dict mapping fixture_id -> response info.

    Returns a list of TestResult (one per assertion).
    Every checked property emits either PASS or FAIL for audit symmetry.
    """
    results = []
    fid = fixture["id"]
    fpath = resolve_fixture_path(fixture)

    expected_exit = fixture["expected_exit_code"]
    expected_decision = fixture.get("expected_decision")
    expected_violations = fixture.get("expected_policy_violations")

    corpus_provider = _build_corpus_provider(corpus_responses, fid)

    try:
        actual_exit, result_dict = vr_module.run(
            str(fpath),
            config=HARNESS_VALIDATOR_CONFIG,
            provider=corpus_provider,
            system_prompt=HARNESS_SYSTEM_PROMPT,
            taxonomy=HARNESS_TAXONOMY,
        )
    except (vr_module.ValidatorError, vr_module.SchemaError) as exc:
        results.append(TestResult(
            fid, "validator", False,
            f"validator_runner.run() error: {exc}",
            f"exit {expected_exit}", str(exc),
        ))
        return results
    except Exception as exc:
        results.append(TestResult(
            fid, "validator", False,
            f"validator_runner.run() raised {type(exc).__name__}: {exc}",
            f"exit {expected_exit}", str(exc),
        ))
        return results

    # --- Exit code assertion ---
    if actual_exit != expected_exit:
        results.append(TestResult(
            fid, "validator", False,
            f"Expected exit {expected_exit}, got exit {actual_exit}",
            expected_exit, actual_exit,
        ))
    else:
        results.append(TestResult(
            fid, "validator", True,
            f"Exit code {actual_exit} matches expected",
            expected_exit, actual_exit,
        ))

    # Exits that should not yield a structured result
    if expected_exit in _NO_PROVIDER_EXIT_CODES:
        if result_dict is not None:
            results.append(TestResult(
                fid, "validator", False,
                f"Expected no result for exit {expected_exit}, "
                f"got result dict",
                None, "result dict present",
            ))
        else:
            results.append(TestResult(
                fid, "validator", True,
                f"No result dict for exit {expected_exit} as expected",
                None, None,
            ))
        return results

    if expected_exit == 3:
        if result_dict is not None:
            results.append(TestResult(
                fid, "validator", False,
                "Expected no result dict for SCHEMA_FAULT",
                None, "result dict present",
            ))
        else:
            results.append(TestResult(
                fid, "validator", True,
                "No result dict for SCHEMA_FAULT as expected",
                None, None,
            ))
        return results

    if result_dict is None:
        results.append(TestResult(
            fid, "validator", False,
            "No result dict returned but expected a structured result",
            "result dict", None,
        ))
        return results

    # --- Decision assertion ---
    actual_decision = result_dict.get("decision")
    if expected_decision is not None:
        if actual_decision != expected_decision:
            results.append(TestResult(
                fid, "validator", False,
                f"Expected decision '{expected_decision}', "
                f"got '{actual_decision}'",
                expected_decision, actual_decision,
            ))
        else:
            results.append(TestResult(
                fid, "validator", True,
                f"Decision '{actual_decision}' matches expected",
                expected_decision, actual_decision,
            ))

    # --- Policy violations assertion ---
    if expected_violations is not None:
        actual_violations = sorted(
            v["rule_id"] for v in result_dict.get("policy_violations", [])
        )
        expected_sorted = sorted(expected_violations)
        if actual_violations != expected_sorted:
            results.append(TestResult(
                fid, "validator", False,
                "Policy violations mismatch",
                expected_sorted, actual_violations,
            ))
        else:
            results.append(TestResult(
                fid, "validator", True,
                f"Policy violations match: {actual_violations}",
                expected_sorted, actual_violations,
            ))

    # --- Confidence range sanity check ---
    confidence = result_dict.get("confidence")
    if confidence is not None:
        if not (0.0 <= confidence <= 1.0):
            results.append(TestResult(
                fid, "validator", False,
                f"Confidence {confidence} outside [0.0, 1.0]",
                "0.0 <= c <= 1.0", confidence,
            ))
        else:
            results.append(TestResult(
                fid, "validator", True,
                f"Confidence {confidence} within [0.0, 1.0]",
                "0.0 <= c <= 1.0", confidence,
            ))

    # --- Reasoning non-empty check ---
    reasoning = result_dict.get("reasoning", "")
    if not reasoning:
        results.append(TestResult(
            fid, "validator", False,
            "Reasoning field is empty",
            "non-empty string", reasoning,
        ))
    else:
        results.append(TestResult(
            fid, "validator", True,
            "Reasoning field is non-empty",
            "non-empty string", reasoning,
        ))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Golden corpus test harness for LLM-Wiki pipeline"
    )
    parser.add_argument(
        "--stage", choices=["parser", "validator", "all"], default="all",
        help="Which stage to test (default: all)"
    )
    parser.add_argument(
        "--fixture", type=str, default=None,
        help="Run a single fixture by ID (e.g., ADV-001)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show all assertions, not just failures"
    )
    args = parser.parse_args()

    manifest = load_manifest()
    check_prerequisites()

    fixtures = manifest["fixtures"]

    # --fixture filters to a single fixture but does NOT filter by stage.
    # The stage flag controls which assertion types run, not which fixtures
    # are visible.
    if args.fixture:
        fixtures = [f for f in fixtures if f["id"] == args.fixture]
        if not fixtures:
            print(f"ERROR: No fixture with ID '{args.fixture}'",
                  file=sys.stderr)
            sys.exit(2)

    print(f"Golden Corpus Harness")
    print(f"  manifest: {manifest['manifest_version']}")
    print(f"  fixtures: {manifest['fixture_version']}")
    print(f"  taxonomy: {manifest['taxonomy_version']}")
    print(f"  stage filter: {args.stage}")
    print(f"  total fixtures: {len(fixtures)}")
    print(f"{'='*60}")

    all_results = []
    unimplemented_stages = []

    validator_fixtures = [f for f in fixtures if f["stage"] == "validator"]
    integration_fixtures = [f for f in fixtures if f["stage"] == "integration"]

    # --- Parser assertions ---
    parser_eligible = collect_parser_eligible(fixtures, args.stage)
    if parser_eligible:
        print(f"\n--- Parser Assertions "
              f"({len(parser_eligible)} fixtures) ---")
        for fixture in parser_eligible:
            all_results.extend(run_parser_test(fixture))

    # --- Validator assertions ---
    if args.stage in ("validator", "all") and validator_fixtures:
        print(f"\n--- Validator Assertions "
              f"({len(validator_fixtures)} fixtures) ---")

        vr_module = _load_validator_runner()
        corpus_responses = _load_corpus_responses(fixtures)
        print(f"  provider: harness-stub "
              f"(deterministic, {len(corpus_responses)} canned responses)")
        for fixture in validator_fixtures:
            all_results.extend(
                run_validator_test(fixture, vr_module, corpus_responses)
            )

    # --- Integration assertions ---
    if args.stage == "all" and integration_fixtures:
        print(f"\n--- Integration Assertions "
              f"({len(integration_fixtures)} fixtures) ---")
        print("  NOT IMPLEMENTED: requires full pipeline")
        print("  See integration/CTX-001-README.md for manual procedure")
        unimplemented_stages.append(
            f"integration ({len(integration_fixtures)} fixtures)")

    # --- Determine exit code ---
    if not all_results:
        print("\nNo assertions were executed.", file=sys.stderr)
        sys.exit(2)

    all_passed = print_results(all_results, verbose=args.verbose)

    # Exit 1 takes priority: if any assertion failed, report failure
    # regardless of unimplemented stages.
    if not all_passed:
        sys.exit(1)

    # Exit 3: all executed assertions passed, but some stages have no
    # assertion runner yet. This is NOT a test failure — the work that
    # was tested is green. But the harness cannot claim full coverage.
    if unimplemented_stages:
        print(f"\nPartial coverage. Unimplemented stages:")
        for s in unimplemented_stages:
            print(f"  - {s}")
        print("Exit 3: all executed assertions passed, "
              "but full coverage requires implementing the above stages.")
        sys.exit(3)

    # Exit 0: all assertions passed AND all requested stages have runners.
    sys.exit(0)


if __name__ == "__main__":
    main()
