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
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

# ---------------------------------------------------------------------------
# Integration stage constants
# ---------------------------------------------------------------------------
# The integration stage exercises the full orchestration pipeline:
# parse -> validate -> ledger write -> audit -> F7 promotion gate.
#
# This stage hard-requires PowerShell 7+ (pwsh) on the PATH. Windows
# PowerShell 5.1 (powershell.exe) is intentionally NOT used: Run-Validator.ps1
# was historically saved as UTF-8-without-BOM and PS5.1 mis-parses non-ASCII
# bytes in scripts without a BOM. Phase 1.7 removed those characters, but
# the harness still requires pwsh to ensure no future regression.
INTEGRATION_TIMEOUT_SECONDS = 60
RUN_VALIDATOR_PATH = SCRIPT_DIR.parent / "Run-Validator.ps1"
INTEGRATION_FIXTURE_ID = "CTX-001"

_LEDGER_NAME_PATTERN = re.compile(r"^[0-9a-f]{64}_\d{8}T\d+Z\.json$")
_AUDIT_NAME_PATTERN = re.compile(r"^promotion-preview-[0-9a-f]{12}\.json$")
_REQUIRED_LEDGER_FIELDS = (
    "decision",
    "source_id",
    "repo_relative_path",
    "document_hash",
    "context_digest",
    "model_config_snapshot",
    "created_utc",
)
_REQUIRED_AUDIT_FIELDS = (
    "source_id",
    "branch_alias",
    "local_tree_fingerprint",
    "destination_path",
)
# ---------------------------------------------------------------------------
# Promote-local stage constants
# ---------------------------------------------------------------------------
# The promote-local stage exercises Promote-ToVerified.ps1 directly (not via
# Run-Validator.ps1) to verify the local-git half of TD-002: branch + copy +
# commit in an isolated worktree, audit-preview population, and JSONL fault
# emission on rollback.  No live Gitea calls are made: LLM_WIKI_GITEA_MOCK_MODE
# returns canned "no remote PR / branch not found" shapes.
PROMOTE_TIMEOUT_SECONDS = 60
PROMOTE_SCRIPT_PATH = SCRIPT_DIR.parent / "Promote-ToVerified.ps1"
PARSE_IDENTITY_PATH = SCRIPT_DIR.parent / "parse_identity.py"
PROMOTE_LOCAL_FIXTURE_REL = "approve/A-001-clean-article.md"
_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_BRANCH_ALIAS_PATTERN = re.compile(r"^auto/[A-Za-z0-9_\-]+/[0-9a-f]{8}$")


_DETERMINISM_STRIP_FIELDS = frozenset({
    "timestamp_utc",
    "created_utc",
    "reviewer_timestamp",
    "ledger_path",
    # repo_root differs between runs because each run uses a fresh temp dir.
    # The transaction-key fields (source_id, repo_relative_path, document_hash,
    # context_digest) remain stable because the relative path is the same
    # ("provisional/<file>") and origin_main_marker collapses to "no-git-head"
    # in both runs.
    "repo_root",
    # promotion_error and stderr embed the full Promote-ToVerified.ps1
    # throw message, which itself includes the temp audit-file path. The
    # canonical fault identity is captured in (fmea_ref, message), which
    # the per-run assertions verify directly. Stripping these for the
    # determinism comparison preserves the byte-equality guarantee for
    # everything that is genuinely deterministic.
    "promotion_error",
    "stderr",
    # Phase 1.9 / 03b: the new local-git commit SHA depends on the commit's
    # author/committer timestamp, which varies by construction across runs.
    # The same SHA appears as commit_sha (in promotion_completed) and
    # pushed_sha (in promotion_push_completed); strip both.
    "commit_sha",
    "pushed_sha",
    "local_commit_sha",
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


# ---------------------------------------------------------------------------
# Integration stage helpers
# ---------------------------------------------------------------------------
def _check_pwsh_available():
    """Return absolute path to pwsh if available, else None.

    Hard-requires pwsh (PowerShell 7+).  powershell.exe (5.1) is intentionally
    not consulted - see INTEGRATION_TIMEOUT_SECONDS comment block above.
    """
    return shutil.which("pwsh")


def _strip_for_determinism(obj):
    """Strip timestamp/ledger_path fields recursively for determinism comparison.

    The integration stage's determinism check compares two runs of the same
    fixture under identical config.  Timestamps and ledger paths differ by
    construction across runs (sub-second filename suffix, temp-dir-specific
    paths) and must be excluded from byte comparison.
    """
    if isinstance(obj, dict):
        return {
            k: _strip_for_determinism(v)
            for k, v in obj.items()
            if k not in _DETERMINISM_STRIP_FIELDS
        }
    if isinstance(obj, list):
        return [_strip_for_determinism(x) for x in obj]
    return obj


def _parse_jsonl_log(log_path):
    """Parse the orchestration JSONL log and return a list of event dicts.

    Lines that fail to parse are silently skipped - any structural problem
    surfaces in downstream count assertions ("expected 1 evaluation_completed,
    got 0").
    """
    if not log_path.exists():
        return []
    events = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _read_state_outputs(state_dir):
    """Read JSONL events, ledger entries, and audit files from a state dir."""
    log_path = state_dir / "logs" / "pipeline.log"
    events = _parse_jsonl_log(log_path)

    ledger_entries = []
    ledger_dir = state_dir / "ledger"
    if ledger_dir.exists():
        for f in sorted(ledger_dir.iterdir()):
            if f.is_file() and f.suffix == ".json":
                try:
                    with open(f, encoding="utf-8") as fh:
                        ledger_entries.append((f.name, json.load(fh)))
                except (OSError, json.JSONDecodeError):
                    ledger_entries.append((f.name, None))

    audit_entries = []
    audit_dir = state_dir / "audit"
    if audit_dir.exists():
        for f in sorted(audit_dir.iterdir()):
            if f.is_file() and f.suffix == ".json":
                try:
                    with open(f, encoding="utf-8") as fh:
                        audit_entries.append((f.name, json.load(fh)))
                except (OSError, json.JSONDecodeError):
                    audit_entries.append((f.name, None))

    return {
        "events": events,
        "ledger_entries": ledger_entries,
        "audit_entries": audit_entries,
    }


def _run_orchestration_once(pwsh_path, fixture_path, work_root, env_overrides):
    """Stage fixture in a temp provisional dir, run Run-Validator.ps1 once.

    Args:
        pwsh_path: absolute path to pwsh executable.
        fixture_path: path to the integration fixture .md.
        work_root: pre-created Path to a temp dir.  This function creates
                   work_root/state and work_root/provisional inside it.
                   Used as -RepoRoot so Get-RepoRelativePath accepts the
                   temp provisional file (the real repo root would reject
                   it as outside-the-tree).
        env_overrides: dict of env var overrides (e.g., LLM_WIKI_STUB_DECISION).
                       ANTHROPIC_API_KEY is always removed from the subprocess
                       env to force the stub provider via credential-aware
                       fallback in Run-Validator.ps1.

    Returns dict with: returncode, stdout, stderr, events, ledger_entries,
    audit_entries, provisional_dir, state_dir, feedback_sidecars.

    Raises subprocess.TimeoutExpired if the orchestration hangs.
    """
    state_dir = work_root / "state"
    provisional_dir = work_root / "provisional"
    verified_dir = work_root / "verified"
    state_dir.mkdir(exist_ok=True)
    provisional_dir.mkdir(exist_ok=True)
    verified_dir.mkdir(exist_ok=True)

    # Phase 1.9 / 03b: initialize work_root as a real git repo so the new
    # local-git + push + PR flow can run end-to-end against the pr_success
    # mock.  Pre-Phase-1.9 the integration stage threw at the credentials
    # gate before reaching local-git, so a non-git work_root was acceptable.
    # Now we go all the way to PR creation, which requires a real worktree
    # operation rooted at -RepoRoot.
    (provisional_dir / ".gitkeep").write_text("")
    (verified_dir / ".gitkeep").write_text("")
    subprocess.run(
        ["git", "init", "-q"],
        cwd=work_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "integration@harness.local"],
        cwd=work_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "integration-harness"],
        cwd=work_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "-q", "-b", "main"],
        cwd=work_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=work_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=work_root, check=True, capture_output=True,
    )

    # Stage the fixture LAST so it does not enter git history.
    staged = provisional_dir / fixture_path.name
    shutil.copy2(fixture_path, staged)

    env = os.environ.copy()
    env.update(env_overrides)
    env.pop("ANTHROPIC_API_KEY", None)

    cmd = [
        pwsh_path,
        "-NoProfile",
        "-NonInteractive",
        "-File",
        str(RUN_VALIDATOR_PATH),
        "-RepoRoot",
        str(work_root),
        "-StateRoot",
        str(state_dir),
        "-ProvisionalRoot",
        str(provisional_dir),
        "-VerifiedRoot",
        str(verified_dir),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=INTEGRATION_TIMEOUT_SECONDS,
        env=env,
    )

    outputs = _read_state_outputs(state_dir)
    feedback_sidecars = sorted(provisional_dir.glob("*.feedback.md"))

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "events": outputs["events"],
        "ledger_entries": outputs["ledger_entries"],
        "audit_entries": outputs["audit_entries"],
        "provisional_dir": provisional_dir,
        "state_dir": state_dir,
        "feedback_sidecars": feedback_sidecars,
    }


def _is_empty_value(val):
    """Return True if val is None, empty string, empty dict, or empty list."""
    if val is None:
        return True
    if isinstance(val, str) and val == "":
        return True
    if isinstance(val, (dict, list)) and len(val) == 0:
        return True
    return False


def _assert_orchestration_run(label, expected_decision, run_data):
    """Apply the per-run integration assertions. Returns list[TestResult]."""
    results = []

    def add(passed, message, expected, actual):
        results.append(
            TestResult(label, "integration", passed, message, expected, actual)
        )

    # --- subprocess exit ---
    rc = run_data["returncode"]
    if rc == 0:
        add(True, "subprocess exit code is 0", 0, rc)
    else:
        stderr_excerpt = (run_data.get("stderr") or "")[:600]
        add(
            False,
            f"subprocess exit code is 0 (got {rc}). stderr excerpt: {stderr_excerpt}",
            0,
            rc,
        )

    events = run_data["events"]

    # --- run_started ---
    started = [e for e in events if e.get("event_type") == "run_started"]
    add(
        len(started) == 1,
        f"exactly one run_started event ({len(started)} found)",
        1,
        len(started),
    )

    # --- evaluation_completed ---
    completed = [e for e in events if e.get("event_type") == "evaluation_completed"]
    add(
        len(completed) == 1,
        f"exactly one evaluation_completed event ({len(completed)} found)",
        1,
        len(completed),
    )

    if completed:
        ec = completed[0]
        add(
            ec.get("decision") == expected_decision,
            f"evaluation_completed.decision == '{expected_decision}'",
            expected_decision,
            ec.get("decision"),
        )
        actual_exit = ec.get("exit_code")
        add(
            actual_exit in (0, 1, 2),
            f"evaluation_completed.exit_code in {{0,1,2}} (got {actual_exit})",
            "in {0,1,2}",
            actual_exit,
        )

    # --- operational_fault (Phase 1.9 / 03b: F7 allowlist inverted) ---
    # All decision paths now expect 0 operational_fault events.  The Phase 1.7
    # F7 fault on approve was a placeholder for "TD-002 not yet wired"; with
    # 03b's pr_success mock-mode flow, PR creation succeeds and no fault fires.
    op_faults = [e for e in events if e.get("event_type") == "operational_fault"]
    add(
        len(op_faults) == 0,
        f"operational_fault count == 0 (Phase 1.9: F7 allowlist inverted; {len(op_faults)} found)",
        0,
        len(op_faults),
    )

    # --- promotion_completed (positive assertion for approve only) ---
    promotion_events = [e for e in events if e.get("event_type") == "promotion_completed"]
    expected_promotion_count = 1 if expected_decision == "approve" else 0
    add(
        len(promotion_events) == expected_promotion_count,
        f"promotion_completed count == {expected_promotion_count} ({len(promotion_events)} found)",
        expected_promotion_count,
        len(promotion_events),
    )

    if expected_decision == "approve":
        if promotion_events:
            pc = promotion_events[0]
            add(
                pc.get("pr_number") == 1,
                "promotion_completed.pr_number == 1 (mocked PR id)",
                1,
                pc.get("pr_number"),
            )
            branch_alias = pc.get("branch_alias")
            add(
                isinstance(branch_alias, str) and branch_alias.startswith("auto/"),
                "promotion_completed.branch_alias starts with 'auto/'",
                "starts with auto/",
                branch_alias,
            )
            commit_sha = pc.get("commit_sha")
            add(
                isinstance(commit_sha, str) and len(commit_sha) >= 40,
                "promotion_completed.commit_sha is a 40-char hex string",
                "40-char hex",
                f"length={len(commit_sha) if isinstance(commit_sha, str) else 'n/a'}",
            )
            add(
                pc.get("pushed_to_remote") is True,
                "promotion_completed.pushed_to_remote == True (push path exercised)",
                True,
                pc.get("pushed_to_remote"),
            )
            add(
                pc.get("tree_sha_check") == "skipped",
                "promotion_completed.tree_sha_check == 'skipped' (no orphan branch in mock)",
                "skipped",
                pc.get("tree_sha_check"),
            )
        else:
            # Pad with no-op failures so the assertion count matches the success
            # path (5 sub-assertions).  Each reports the missing-event explicitly.
            for missing_label in (
                "promotion_completed.pr_number",
                "promotion_completed.branch_alias",
                "promotion_completed.commit_sha",
                "promotion_completed.pushed_to_remote",
                "promotion_completed.tree_sha_check",
            ):
                add(
                    False,
                    f"{missing_label}: missing (no promotion_completed event present)",
                    "field present",
                    "no event",
                )

    # --- run_completed ---
    completed_run = [e for e in events if e.get("event_type") == "run_completed"]
    add(
        len(completed_run) == 1,
        f"exactly one run_completed event ({len(completed_run)} found)",
        1,
        len(completed_run),
    )

    if completed_run:
        summary = completed_run[0].get("summary", {}) or {}
        actual_faults = summary.get("faults", 0)
        # Phase 1.9 / 03b: F7 allowlist inverted - all decisions expect 0 faults.
        add(
            actual_faults == 0,
            f"run_completed.summary.faults == 0 ({actual_faults} found)",
            0,
            actual_faults,
        )

    # --- ledger ---
    ledger_entries = run_data["ledger_entries"]
    add(
        len(ledger_entries) == 1,
        f"exactly one ledger file ({len(ledger_entries)} found)",
        1,
        len(ledger_entries),
    )

    if ledger_entries:
        fname, entry = ledger_entries[0]
        add(
            _LEDGER_NAME_PATTERN.match(fname) is not None,
            f"ledger filename matches <64hex>_<timestamp>.json (got {fname})",
            "<64hex>_<timestamp>.json",
            fname,
        )

        add(
            entry is not None,
            "ledger entry parses as JSON",
            "valid JSON",
            "parse error" if entry is None else "ok",
        )

        if entry is not None:
            for field in _REQUIRED_LEDGER_FIELDS:
                val = entry.get(field)
                empty = _is_empty_value(val)
                add(
                    not empty,
                    f"ledger field '{field}' present and non-empty",
                    "non-empty value",
                    repr(val)[:60],
                )

            add(
                entry.get("decision") == expected_decision,
                f"ledger entry decision == '{expected_decision}'",
                expected_decision,
                entry.get("decision"),
            )

            svr = entry.get("schema_validated_result")
            try:
                from schema_helpers import (
                    load_schema,
                    validate as schema_validate,
                )

                schema = load_schema()
                if isinstance(svr, dict):
                    schema_errors = schema_validate(svr, schema)
                else:
                    schema_errors = [("(root)", "not a JSON object")]
                add(
                    not schema_errors,
                    "ledger schema_validated_result validates against validation_result.schema.json",
                    "0 errors",
                    f"{len(schema_errors)} errors" if schema_errors else "ok",
                )
            except Exception as exc:
                add(
                    False,
                    f"ledger schema validation could not be performed: {exc}",
                    "validation runs",
                    str(exc)[:60],
                )

    # --- audit promotion-preview (only for approve) ---
    audit_entries = run_data["audit_entries"]
    preview_entries = [
        (n, c) for (n, c) in audit_entries if n.startswith("promotion-preview-")
    ]
    sidecars = run_data.get("feedback_sidecars", [])

    if expected_decision == "approve":
        add(
            len(preview_entries) == 1,
            f"exactly one promotion-preview audit file ({len(preview_entries)} found)",
            1,
            len(preview_entries),
        )
        if preview_entries:
            pname, pcontent = preview_entries[0]
            add(
                _AUDIT_NAME_PATTERN.match(pname) is not None,
                f"audit filename matches promotion-preview-<docHash12>.json (got {pname})",
                "promotion-preview-<docHash12>.json",
                pname,
            )
            add(
                pcontent is not None,
                "audit file parses as JSON",
                "valid JSON",
                "parse error" if pcontent is None else "ok",
            )
            if pcontent is not None:
                for field in _REQUIRED_AUDIT_FIELDS:
                    val = pcontent.get(field)
                    add(
                        not _is_empty_value(val),
                        f"audit field '{field}' present and non-empty",
                        "non-empty value",
                        repr(val)[:60],
                    )
        add(
            len(sidecars) == 0,
            f"no feedback sidecar for approve ({len(sidecars)} found)",
            0,
            len(sidecars),
        )
    else:
        add(
            len(preview_entries) == 0,
            f"no promotion-preview audit file for {expected_decision} ({len(preview_entries)} found)",
            0,
            len(preview_entries),
        )
        add(
            len(sidecars) == 1,
            f"exactly one feedback sidecar for {expected_decision} ({len(sidecars)} found)",
            1,
            len(sidecars),
        )

    return results


def _assert_determinism(label, run_a, run_b):
    """Compare two runs and assert ledger + JSONL byte-equality (modulo timestamps)."""
    results = []

    def add(passed, message, expected, actual):
        results.append(
            TestResult(label, "integration", passed, message, expected, actual)
        )

    # Ledger comparison
    if len(run_a["ledger_entries"]) != 1 or len(run_b["ledger_entries"]) != 1:
        add(
            False,
            f"determinism: cannot compare ledgers "
            f"(run_a={len(run_a['ledger_entries'])}, run_b={len(run_b['ledger_entries'])})",
            "1 ledger each",
            f"a={len(run_a['ledger_entries'])} b={len(run_b['ledger_entries'])}",
        )
    else:
        a = _strip_for_determinism(run_a["ledger_entries"][0][1])
        b = _strip_for_determinism(run_b["ledger_entries"][0][1])
        ok = a == b
        add(
            ok,
            "two approve runs produce byte-identical ledger contents (modulo timestamps)",
            "identical",
            "differs" if not ok else "match",
        )

    a_events = [_strip_for_determinism(e) for e in run_a["events"]]
    b_events = [_strip_for_determinism(e) for e in run_b["events"]]
    ok = a_events == b_events
    add(
        ok,
        "two approve runs produce byte-identical JSONL event sequences "
        "(modulo timestamps and ledger_path)",
        "identical",
        "differs" if not ok else "match",
    )

    return results


def run_integration_tests(integration_fixtures):
    """Run the integration assertions against the integration-stage fixtures.

    Exercises approve / reject / escalate decision paths via the
    LLM_WIKI_STUB_DECISION env override, then re-runs approve a fourth time
    purely for determinism comparison.

    Returns (results, skipped_reason_or_None).  When skipped_reason is set,
    the caller should add the integration stage to unimplemented_stages
    rather than treating the empty result list as a failure.
    """
    pwsh_path = _check_pwsh_available()
    if pwsh_path is None:
        return [], (
            "pwsh (PowerShell 7+) not found on PATH. The integration stage "
            "requires pwsh; powershell.exe (5.1) is intentionally not used. "
            "Install PowerShell 7+ to enable integration tests."
        )

    if not RUN_VALIDATOR_PATH.exists():
        return [
            TestResult(
                INTEGRATION_FIXTURE_ID,
                "integration",
                False,
                f"Run-Validator.ps1 not found: {RUN_VALIDATOR_PATH}",
                "script exists",
                "missing",
            )
        ], None

    if not integration_fixtures:
        return [], None

    fixture = integration_fixtures[0]
    fixture_path = resolve_fixture_path(fixture)
    if not fixture_path.exists():
        return [
            TestResult(
                fixture["id"],
                "integration",
                False,
                f"integration fixture not found: {fixture_path}",
                "file exists",
                "missing",
            )
        ], None

    all_results = []
    canonical_approve_run = None

    runs = (
        ("CTX-001:approve", "approve", True),
        ("CTX-001:reject", "reject", False),
        ("CTX-001:escalate", "escalate", False),
        ("CTX-001:approve-2", "approve", False),
    )

    for label, decision, capture in runs:
        work_root = Path(tempfile.mkdtemp(prefix="llm-wiki-itest-"))
        try:
            try:
                run_data = _run_orchestration_once(
                    pwsh_path=pwsh_path,
                    fixture_path=fixture_path,
                    work_root=work_root,
                    env_overrides={
                        "LLM_WIKI_STUB_DECISION": decision,
                        # Phase 1.9 / 03b: drive the post-DryRun flow under the
                        # pr_success mock so the integration stage exercises
                        # local-git + push + PR creation end-to-end without
                        # contacting any live Gitea.
                        "LLM_WIKI_GITEA_MOCK_MODE": "pr_success",
                        "GITEA_URL":         "https://mock.local",
                        "GITEA_TOKEN":       "mock-token",
                        "GITEA_REPO_OWNER":  "mock-owner",
                        "GITEA_REPO_NAME":   "mock-repo",
                        "GITEA_BASE_BRANCH": "main",
                    },
                )
            except subprocess.TimeoutExpired:
                all_results.append(
                    TestResult(
                        label,
                        "integration",
                        False,
                        f"orchestration subprocess hung "
                        f"(timeout after {INTEGRATION_TIMEOUT_SECONDS}s)",
                        "completes within timeout",
                        "subprocess hung",
                    )
                )
                continue

            if label == "CTX-001:approve-2":
                if canonical_approve_run is not None:
                    all_results.extend(
                        _assert_determinism(
                            "CTX-001:determinism",
                            canonical_approve_run,
                            run_data,
                        )
                    )
                else:
                    all_results.append(
                        TestResult(
                            "CTX-001:determinism",
                            "integration",
                            False,
                            "determinism check skipped: first approve run did "
                            "not produce a comparable result",
                            "comparable run",
                            "missing",
                        )
                    )
            else:
                all_results.extend(
                    _assert_orchestration_run(label, decision, run_data)
                )
                if capture:
                    canonical_approve_run = run_data
        finally:
            try:
                shutil.rmtree(work_root, ignore_errors=False)
            except OSError as exc:
                # Windows can fail to remove files locked by subprocess descendants.
                # Don't fail the stage on cleanup error - assertions are already done.
                print(
                    f"WARNING: cleanup of {work_root} failed: {exc}",
                    file=sys.stderr,
                )

    return all_results, None


# ---------------------------------------------------------------------------
# Promote-local stage helpers (TD-002 part 1)
# ---------------------------------------------------------------------------
def _setup_promote_local_repo(work_root, fixture_path):
    """Initialize a temp git repo for the promote-local stage.

    Creates work_root/<.git, pipeline/{provisional,verified}, parse_identity.py,
    Promote-ToVerified.ps1>, makes one initial commit on main, and stages the
    fixture into pipeline/provisional/.
    """
    pipeline_dir = work_root / "pipeline"
    provisional_dir = pipeline_dir / "provisional"
    verified_dir = pipeline_dir / "verified"
    state_dir = work_root / "state"
    pipeline_dir.mkdir(parents=True)
    provisional_dir.mkdir()
    verified_dir.mkdir()
    state_dir.mkdir()
    (provisional_dir / ".gitkeep").write_text("")
    (verified_dir / ".gitkeep").write_text("")

    # Copy the script under test and its parser dependency into the temp repo.
    shutil.copy2(PROMOTE_SCRIPT_PATH, pipeline_dir / "Promote-ToVerified.ps1")
    shutil.copy2(PARSE_IDENTITY_PATH, pipeline_dir / "parse_identity.py")

    # git init + initial commit on main.
    subprocess.run(
        ["git", "init", "-q"], cwd=work_root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "promote-local@harness.local"],
        cwd=work_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "promote-local-harness"],
        cwd=work_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "-q", "-b", "main"],
        cwd=work_root, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=work_root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=work_root, check=True, capture_output=True,
    )

    # Stage the fixture LAST so it does not enter git history.
    staged = provisional_dir / fixture_path.name
    shutil.copy2(fixture_path, staged)

    return {
        "pipeline_dir": pipeline_dir,
        "provisional_dir": provisional_dir,
        "verified_dir": verified_dir,
        "state_dir": state_dir,
        "staged_article": staged,
        "promote_script": pipeline_dir / "Promote-ToVerified.ps1",
    }


def _run_promote(pwsh_path, repo, work_root, dry_run, env_overrides=None):
    """Invoke Promote-ToVerified.ps1 in the temp repo with mocked Gitea.

    Returns dict with returncode, stdout, stderr, audit_files (list of
    (path, parsed_json or None)), jsonl_events (list of dicts).

    env_overrides (optional): merged on top of the default mock env.  Used by
    promote-full to switch mock modes (pr_success, pr_fail, push_fail,
    existing_open_pr).  Default behavior (LLM_WIKI_GITEA_MOCK_MODE=local_only)
    is preserved when env_overrides is None - matches Phase 1.8 contract.
    """
    env = os.environ.copy()
    env["LLM_WIKI_GITEA_MOCK_MODE"] = "local_only"
    env["GITEA_URL"] = "https://mock.local"
    env["GITEA_TOKEN"] = "mock-token"
    env["GITEA_REPO_OWNER"] = "mock-owner"
    env["GITEA_REPO_NAME"] = "mock-repo"
    env.pop("ANTHROPIC_API_KEY", None)
    if env_overrides:
        env.update(env_overrides)

    cmd = [
        pwsh_path,
        "-NoProfile",
        "-NonInteractive",
        "-File",
        str(repo["promote_script"]),
        "-ArticlePath", str(repo["staged_article"]),
        "-RepoRoot", str(work_root),
        "-StateRoot", str(repo["state_dir"]),
        "-ProvisionalRoot", str(repo["provisional_dir"]),
        "-VerifiedRoot", str(repo["verified_dir"]),
        "-ContextDigest", "ctx-promote-local-mock",
    ]
    if dry_run:
        cmd.append("-DryRun")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=PROMOTE_TIMEOUT_SECONDS,
        env=env,
    )

    audit_dir = repo["state_dir"] / "audit"
    audit_files = []
    if audit_dir.exists():
        for f in sorted(audit_dir.iterdir()):
            if f.is_file() and f.suffix == ".json":
                try:
                    with open(f, encoding="utf-8") as fh:
                        audit_files.append((f.name, json.load(fh)))
                except (OSError, json.JSONDecodeError):
                    audit_files.append((f.name, None))

    jsonl_events = _parse_jsonl_log(repo["state_dir"] / "logs" / "pipeline.log")

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "audit_files": audit_files,
        "jsonl_events": jsonl_events,
    }


def _cleanup_promote_local_worktrees(work_root):
    """Best-effort: remove any worktrees the test created and the temp dir.

    The promote-local test creates a worktree under %TEMP%\\llm-wiki-promote-*
    that is intentionally left in place by the script.  This helper cleans
    those orphans up after the test runs so they don't accumulate.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(work_root), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10,
        )
        # Each block: "worktree <path>\nHEAD ...\nbranch ..."
        # Only target worktrees the script created (basename
        # starts with 'llm-wiki-promote-' but is NOT the test's
        # outer work_root, which uses 'llm-wiki-promote-local-').
        for line in (result.stdout or "").splitlines():
            if not line.startswith("worktree "):
                continue
            wt_path = line[len("worktree "):].strip()
            base = Path(wt_path).name
            if base.startswith("llm-wiki-promote-") and "-local-" not in base:
                subprocess.run(
                    ["git", "-C", str(work_root),
                     "worktree", "remove", "--force", wt_path],
                    capture_output=True, timeout=10,
                )
    except (subprocess.TimeoutExpired, OSError):
        pass


def _assert_dry_run(label, run_data):
    """Assertions for the -DryRun invocation."""
    results = []

    def add(passed, message, expected, actual):
        results.append(TestResult(label, "promote-local", passed, message, expected, actual))

    rc = run_data["returncode"]
    add(rc == 0, f"dry-run exit code is 0 (got {rc})", 0, rc)

    audit_files = run_data["audit_files"]
    add(
        len(audit_files) == 1,
        f"dry-run produced exactly one audit file ({len(audit_files)} found)",
        1, len(audit_files),
    )
    if audit_files:
        name, content = audit_files[0]
        add(
            _AUDIT_NAME_PATTERN.match(name) is not None,
            f"audit filename matches promotion-preview-<docHash12>.json (got {name})",
            "promotion-preview-<docHash12>.json", name,
        )
        add(content is not None, "audit file parses as JSON",
            "valid JSON", "parse error" if content is None else "ok")
        if content is not None:
            for field in _REQUIRED_AUDIT_FIELDS:
                val = content.get(field)
                add(
                    not _is_empty_value(val),
                    f"audit field '{field}' present and non-empty",
                    "non-empty value", repr(val)[:60],
                )
            # New fields from TD-002 part 1: present in dry-run with null values.
            add(
                "local_commit_sha" in content,
                "audit has 'local_commit_sha' key (dry-run)",
                "key present", list(content.keys())[:8],
            )
            add(
                content.get("local_commit_sha") is None,
                "dry-run audit local_commit_sha is null",
                None, content.get("local_commit_sha"),
            )
            add(
                "worktree_path" in content,
                "audit has 'worktree_path' key (dry-run)",
                "key present", list(content.keys())[:8],
            )
            add(
                content.get("worktree_path") is None,
                "dry-run audit worktree_path is null",
                None, content.get("worktree_path"),
            )

    # No JSONL faults should fire in dry-run.
    faults = [e for e in run_data["jsonl_events"]
              if e.get("event_type") == "operational_fault"]
    add(
        len(faults) == 0,
        f"dry-run emits no operational_fault events ({len(faults)} found)",
        0, len(faults),
    )

    return results


def _assert_live_run(label, run_data):
    """Assertions for the live (non-DryRun) invocation."""
    results = []

    def add(passed, message, expected, actual):
        results.append(TestResult(label, "promote-local", passed, message, expected, actual))

    # Promote always throws until 03b is wired, so non-zero exit is expected.
    rc = run_data["returncode"]
    add(rc != 0, f"live-run exit code is non-zero (got {rc})",
        "non-zero", rc)

    stderr = run_data.get("stderr") or ""
    stdout = run_data.get("stdout") or ""
    combined = stderr + "\n" + stdout
    add(
        "promotion_gated_pending_remote_wiring" in combined,
        "live-run output contains 'promotion_gated_pending_remote_wiring'",
        "substring present",
        "missing" if "promotion_gated_pending_remote_wiring" not in combined else "ok",
    )
    add(
        "TD-002 part 2" in combined,
        "live-run output references 'TD-002 part 2'",
        "substring present",
        "missing" if "TD-002 part 2" not in combined else "ok",
    )

    audit_files = run_data["audit_files"]
    add(
        len(audit_files) == 1,
        f"live-run produced exactly one audit file ({len(audit_files)} found)",
        1, len(audit_files),
    )

    commit_sha = None
    worktree_path = None
    branch_alias = None
    if audit_files:
        _, content = audit_files[0]
        add(content is not None, "audit file parses as JSON",
            "valid JSON", "parse error" if content is None else "ok")
        if content is not None:
            commit_sha = content.get("local_commit_sha")
            worktree_path = content.get("worktree_path")
            branch_alias = content.get("branch_alias")
            add(
                isinstance(commit_sha, str) and bool(_COMMIT_SHA_PATTERN.match(commit_sha)),
                f"audit local_commit_sha is a 40-char hex (got {commit_sha!r})",
                "40-char hex sha", commit_sha,
            )
            add(
                isinstance(worktree_path, str) and "llm-wiki-promote-" in worktree_path,
                f"audit worktree_path looks like a temp worktree (got {worktree_path!r})",
                "contains 'llm-wiki-promote-'", worktree_path,
            )
            add(
                isinstance(branch_alias, str) and bool(_BRANCH_ALIAS_PATTERN.match(branch_alias)),
                f"audit branch_alias matches auto/<source>/<8-hex> (got {branch_alias!r})",
                "auto/<source>/<8-hex>", branch_alias,
            )

    # Worktree on disk: should exist and contain the article copy.
    if worktree_path:
        wt = Path(worktree_path)
        add(wt.is_dir(), f"worktree path exists on disk ({worktree_path})",
            "directory exists", "missing" if not wt.is_dir() else "ok")
        verified_in_wt = wt / "pipeline" / "verified" / "A-001-clean-article.md"
        add(
            verified_in_wt.is_file(),
            "verified article was copied into the worktree",
            "file present",
            "missing" if not verified_in_wt.is_file() else "ok",
        )
    else:
        add(False, "worktree path missing - downstream checks skipped",
            "non-null path", None)
        add(False, "verified-article check skipped (no worktree path)",
            "file present", "skipped")

    # Commit on the new branch: SHA should match what the audit reported.
    if commit_sha and worktree_path and Path(worktree_path).is_dir():
        head_proc = subprocess.run(
            ["git", "-C", worktree_path, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        head_sha = (head_proc.stdout or "").strip()
        add(
            head_sha == commit_sha,
            f"worktree HEAD == audit local_commit_sha",
            commit_sha, head_sha,
        )

        msg_proc = subprocess.run(
            ["git", "-C", worktree_path, "log", "-1", "--pretty=%s"],
            capture_output=True, text=True, timeout=10,
        )
        commit_msg = (msg_proc.stdout or "").strip()
        add(
            commit_msg.startswith("auto-promote: ") and " (" in commit_msg and commit_msg.endswith(")"),
            f"commit message follows 'auto-promote: <source> (<8-hex>)' (got {commit_msg!r})",
            "auto-promote: <source> (<8-hex>)", commit_msg,
        )
    else:
        add(False, "commit-SHA check skipped (no commit_sha or worktree)",
            "match", "skipped")
        add(False, "commit-message check skipped (no commit_sha or worktree)",
            "auto-promote: <source> (<8-hex>)", "skipped")

    # No PROMOTION_LOCAL_GIT_FAILED faults on the happy path.
    local_git_faults = [
        e for e in run_data["jsonl_events"]
        if e.get("fault_category") == "PROMOTION_LOCAL_GIT_FAILED"
    ]
    add(
        len(local_git_faults) == 0,
        f"happy path emits no PROMOTION_LOCAL_GIT_FAILED faults ({len(local_git_faults)} found)",
        0, len(local_git_faults),
    )

    return results


def _assert_idempotent_rerun(label, run_data):
    """Assertions for the idempotent re-run path under local_only mock.

    Phase 1.9 / 03b extended Invoke-StartupReconciliation to auto-clean
    orphan worktrees whose remote branch is gone (404 in local_only mock).
    The second run therefore succeeds local-git promotion afresh and throws
    at the local_only post-local-git boundary - same shape as the first
    live run, plus a startup reconciliation cleanup line.

    Pre-Phase-1.9 behavior was "fail loudly with branch already exists";
    that contract was explicitly anticipated to change in 03b per the
    Phase 1.8 ledger entry.
    """
    results = []

    def add(passed, message, expected, actual):
        results.append(TestResult(label, "promote-local", passed, message, expected, actual))

    rc = run_data["returncode"]
    add(rc != 0,
        f"rerun exit code is non-zero (local_only still throws post-local-git, got {rc})",
        "non-zero", rc)

    combined = (run_data.get("stderr") or "") + "\n" + (run_data.get("stdout") or "")

    add(
        "promotion_gated_pending_remote_wiring" in combined,
        "rerun output contains 'promotion_gated_pending_remote_wiring'",
        "substring present",
        "missing" if "promotion_gated_pending_remote_wiring" not in combined else "ok",
    )

    add(
        "Startup reconciliation removed" in combined,
        "rerun output reports startup reconciliation cleaned an orphan worktree",
        "substring present",
        "missing" if "Startup reconciliation removed" not in combined else "ok",
    )

    # Idempotent-recovery contract: rerun should NOT emit PROMOTION_LOCAL_GIT_FAILED
    # because the orphan was auto-cleaned before Invoke-LocalGitPromotion's
    # branch-already-exists precheck ran.
    local_git_faults = [
        e for e in run_data["jsonl_events"]
        if e.get("fault_category") == "PROMOTION_LOCAL_GIT_FAILED"
    ]
    add(
        len(local_git_faults) == 0,
        f"rerun emits no PROMOTION_LOCAL_GIT_FAILED faults (orphan auto-cleaned, {len(local_git_faults)} found, expected 0)",
        0, len(local_git_faults),
    )

    # The new run should have produced a fresh worktree (different from the
    # first run's, but we don't have cross-run state).  Instead assert that
    # at least one worktree path is named in stdout/stderr - a sanity check
    # that local-git produced a tempdir.
    add(
        "llm-wiki-promote-" in combined,
        "rerun output references a fresh llm-wiki-promote-* worktree path",
        "substring present",
        "missing" if "llm-wiki-promote-" not in combined else "ok",
    )

    return results


def run_promote_local_tests():
    """Run the promote-local stage assertions.

    Exercises Promote-ToVerified.ps1 directly (not via Run-Validator):
      1. -DryRun: audit preview produced with new local_commit_sha/worktree_path keys (null in dry-run)
      2. Live run with mocked Gitea: worktree created, article copied, commit on new branch, post-local-git throw fires
      3. Second live run with same article: idempotent recovery via startup
         reconciliation (orphan worktree from run 2 auto-cleaned, second
         local-git proceeds fresh, post-local-git throw fires again)

    Returns (results, skipped_reason_or_None).
    """
    pwsh_path = _check_pwsh_available()
    if pwsh_path is None:
        return [], (
            "pwsh (PowerShell 7+) not found on PATH. The promote-local stage "
            "requires pwsh; powershell.exe is intentionally not used."
        )

    if not PROMOTE_SCRIPT_PATH.exists():
        return [TestResult(
            "promote-local", "promote-local", False,
            f"Promote-ToVerified.ps1 not found: {PROMOTE_SCRIPT_PATH}",
            "script exists", "missing",
        )], None

    fixture_path = CORPUS_DIR / PROMOTE_LOCAL_FIXTURE_REL
    if not fixture_path.exists():
        return [TestResult(
            "promote-local", "promote-local", False,
            f"Fixture not found: {fixture_path}",
            "file exists", "missing",
        )], None

    all_results = []
    work_root = Path(tempfile.mkdtemp(prefix="llm-wiki-promote-local-"))
    try:
        repo = _setup_promote_local_repo(work_root, fixture_path)

        try:
            dry = _run_promote(pwsh_path, repo, work_root, dry_run=True)
        except subprocess.TimeoutExpired:
            all_results.append(TestResult(
                "promote-local:dry-run", "promote-local", False,
                f"dry-run hung (timeout after {PROMOTE_TIMEOUT_SECONDS}s)",
                "completes within timeout", "subprocess hung",
            ))
        else:
            all_results.extend(_assert_dry_run("promote-local:dry-run", dry))

        try:
            live = _run_promote(pwsh_path, repo, work_root, dry_run=False)
        except subprocess.TimeoutExpired:
            all_results.append(TestResult(
                "promote-local:live", "promote-local", False,
                f"live-run hung (timeout after {PROMOTE_TIMEOUT_SECONDS}s)",
                "completes within timeout", "subprocess hung",
            ))
        else:
            all_results.extend(_assert_live_run("promote-local:live", live))

        # Second live run: orphan worktree from run 2 should be auto-cleaned
        # by Invoke-StartupReconciliation (Phase 1.9 / 03b worktree-orphan
        # sweep), then a fresh local-git promotion runs and throws again at
        # the local_only post-local-git boundary.
        try:
            second = _run_promote(pwsh_path, repo, work_root, dry_run=False)
        except subprocess.TimeoutExpired:
            all_results.append(TestResult(
                "promote-local:rerun", "promote-local", False,
                f"second live-run hung (timeout after {PROMOTE_TIMEOUT_SECONDS}s)",
                "completes within timeout", "subprocess hung",
            ))
        else:
            all_results.extend(_assert_idempotent_rerun("promote-local:rerun", second))
    finally:
        _cleanup_promote_local_worktrees(work_root)
        try:
            shutil.rmtree(work_root, ignore_errors=False)
        except OSError as exc:
            print(f"WARNING: cleanup of {work_root} failed: {exc}",
                  file=sys.stderr)

    return all_results, None


# ---------------------------------------------------------------------------
# promote-full stage (Phase 1.9 / TD-002 part 2)
# ---------------------------------------------------------------------------
# Exercises the full Promote-ToVerified.ps1 flow under the new mock modes
# introduced by 03b: pr_success (happy path), push_fail (rollback after
# local-git, before push success), pr_fail (rollback after push success,
# remote branch deletion), existing_open_pr (idempotent re-run short-circuit).
#
# Tree-equivalence paths (orphan-recovery: tree_match, tree_mismatch) are
# deferred to a follow-up phase - they need a bare-repo fixture and the real
# fetch path is exercised by the live throwaway smoke test (Stage 8).


def _assert_full_success_path(label, run_data):
    """Happy path: pr_success mock - push mocked, PR creation mocked-success."""
    results = []

    def add(passed, message, expected, actual):
        results.append(TestResult(label, "promote-full", passed, message, expected, actual))

    rc = run_data["returncode"]
    add(rc == 0, f"success-path exit code is 0 ({rc})", 0, rc)

    combined = (run_data.get("stderr") or "") + "\n" + (run_data.get("stdout") or "")
    add(
        "Promotion complete: PR #1" in combined,
        "success-path stdout reports 'Promotion complete: PR #1'",
        "substring present",
        "missing" if "Promotion complete: PR #1" not in combined else "ok",
    )

    # promotion_completed JSONL event with structured fields.
    promotion_events = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "promotion_completed"
    ]
    add(
        len(promotion_events) == 1,
        f"exactly one promotion_completed event ({len(promotion_events)} found)",
        1, len(promotion_events),
    )
    if promotion_events:
        pc = promotion_events[0]
        add(pc.get("pr_number") == 1, "promotion_completed.pr_number == 1", 1, pc.get("pr_number"))
        add(
            isinstance(pc.get("commit_sha"), str) and len(pc["commit_sha"]) >= 40,
            "promotion_completed.commit_sha is 40-char hex",
            "40-char hex",
            f"length={len(pc['commit_sha']) if isinstance(pc.get('commit_sha'), str) else 'n/a'}",
        )
        add(
            isinstance(pc.get("branch_alias"), str) and pc["branch_alias"].startswith("auto/"),
            "promotion_completed.branch_alias starts with 'auto/'",
            "starts with auto/",
            pc.get("branch_alias"),
        )
        add(
            pc.get("pushed_to_remote") is True,
            "promotion_completed.pushed_to_remote == True",
            True,
            pc.get("pushed_to_remote"),
        )

    # promotion_push_completed positive log line.
    push_events = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "promotion_push_completed"
    ]
    add(
        len(push_events) == 1,
        f"exactly one promotion_push_completed event ({len(push_events)} found)",
        1, len(push_events),
    )
    if push_events:
        pe = push_events[0]
        add(
            pe.get("mocked") is True,
            "promotion_push_completed.mocked == True (pr_success mode skipped real push)",
            True, pe.get("mocked"),
        )

    # No operational_fault on success path.
    faults = [e for e in run_data["jsonl_events"] if e.get("event_type") == "operational_fault"]
    add(
        len(faults) == 0,
        f"success path emits no operational_fault events ({len(faults)} found)",
        0, len(faults),
    )

    # Audit file has pr_number=1 and pr_url populated.
    if run_data["audit_files"]:
        audit_name, audit_data = run_data["audit_files"][0]
        if audit_data:
            add(
                audit_data.get("pr_number") == 1,
                "audit.pr_number == 1",
                1, audit_data.get("pr_number"),
            )
            pr_url = audit_data.get("pr_url")
            add(
                isinstance(pr_url, str) and len(pr_url) > 0,
                "audit.pr_url is a non-empty string",
                "non-empty string",
                pr_url,
            )

    return results


def _assert_full_push_fail_path(label, run_data):
    """Push-fail path: push_fail mock - synthetic push failure, rollback expected."""
    results = []

    def add(passed, message, expected, actual):
        results.append(TestResult(label, "promote-full", passed, message, expected, actual))

    rc = run_data["returncode"]
    add(rc != 0, f"push-fail exit code is non-zero ({rc})", "non-zero", rc)

    combined = (run_data.get("stderr") or "") + "\n" + (run_data.get("stdout") or "")
    add(
        "Simulated push failure" in combined,
        "push-fail output references the synthetic push failure",
        "substring present",
        "missing" if "Simulated push failure" not in combined else "ok",
    )

    # PROMOTION_PUSH_FAILED fault should be emitted.
    push_faults = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "operational_fault"
        and e.get("fault_category") == "PROMOTION_PUSH_FAILED"
    ]
    add(
        len(push_faults) >= 1,
        f"push-fail emits >=1 PROMOTION_PUSH_FAILED fault ({len(push_faults)} found)",
        ">=1", len(push_faults),
    )
    if push_faults:
        latest = push_faults[-1]
        add(latest.get("fmea_ref") == "F7", "push fault fmea_ref == 'F7'", "F7", latest.get("fmea_ref"))
        add(
            latest.get("step") == "git_push_promotion",
            "push fault step == 'git_push_promotion'",
            "git_push_promotion", latest.get("step"),
        )

    # No promotion_completed event - rollback prevented progress.
    promotion_events = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "promotion_completed"
    ]
    add(
        len(promotion_events) == 0,
        f"push-fail emits no promotion_completed event ({len(promotion_events)} found)",
        0, len(promotion_events),
    )

    return results


def _assert_full_pr_fail_path(label, run_data):
    """PR-fail-after-push path: pr_fail mock - PR creation API errors after
    push success, remote branch deletion attempted, rollback expected."""
    results = []

    def add(passed, message, expected, actual):
        results.append(TestResult(label, "promote-full", passed, message, expected, actual))

    rc = run_data["returncode"]
    add(rc != 0, f"pr-fail exit code is non-zero ({rc})", "non-zero", rc)

    combined = (run_data.get("stderr") or "") + "\n" + (run_data.get("stdout") or "")
    add(
        "PR creation failed" in combined,
        "pr-fail output references 'PR creation failed'",
        "substring present",
        "missing" if "PR creation failed" not in combined else "ok",
    )
    add(
        "Remote branch cleanup: succeeded" in combined,
        "pr-fail output reports remote branch cleanup attempted (mocked DELETE returns 204)",
        "substring present",
        "missing" if "Remote branch cleanup: succeeded" not in combined else "ok",
    )

    # PROMOTION_PR_FAILED fault should be emitted.
    pr_faults = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "operational_fault"
        and e.get("fault_category") == "PROMOTION_PR_FAILED"
    ]
    add(
        len(pr_faults) >= 1,
        f"pr-fail emits >=1 PROMOTION_PR_FAILED fault ({len(pr_faults)} found)",
        ">=1", len(pr_faults),
    )
    if pr_faults:
        latest = pr_faults[-1]
        add(latest.get("step") == "pr_creation", "pr fault step == 'pr_creation'", "pr_creation", latest.get("step"))

    # promotion_push_completed should still have fired (push completed before PR fail).
    push_events = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "promotion_push_completed"
    ]
    add(
        len(push_events) == 1,
        f"pr-fail emitted push_completed before PR fail ({len(push_events)} found)",
        1, len(push_events),
    )

    # No promotion_completed event.
    promotion_events = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "promotion_completed"
    ]
    add(
        len(promotion_events) == 0,
        f"pr-fail emits no promotion_completed event ({len(promotion_events)} found)",
        0, len(promotion_events),
    )

    return results


def _assert_full_idempotent_path(label, run_data):
    """Idempotent re-run path: existing_open_pr mock - branch + open PR exist,
    Promote should short-circuit at exit 0 with no new push or PR."""
    results = []

    def add(passed, message, expected, actual):
        results.append(TestResult(label, "promote-full", passed, message, expected, actual))

    rc = run_data["returncode"]
    add(rc == 0, f"idempotent re-run exit code is 0 ({rc})", 0, rc)

    combined = (run_data.get("stderr") or "") + "\n" + (run_data.get("stdout") or "")
    add(
        "Existing open PR #1 found" in combined,
        "idempotent path stdout reports 'Existing open PR #1 found'",
        "substring present",
        "missing" if "Existing open PR #1 found" not in combined else "ok",
    )

    # No new promotion_completed event - short-circuit happened.
    promotion_events = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "promotion_completed"
    ]
    add(
        len(promotion_events) == 0,
        f"idempotent path emits no promotion_completed event ({len(promotion_events)} found)",
        0, len(promotion_events),
    )

    # No push event - short-circuit happened before push.
    push_events = [
        e for e in run_data["jsonl_events"]
        if e.get("event_type") == "promotion_push_completed"
    ]
    add(
        len(push_events) == 0,
        f"idempotent path emits no promotion_push_completed event ({len(push_events)} found)",
        0, len(push_events),
    )

    # No operational_fault.
    faults = [e for e in run_data["jsonl_events"] if e.get("event_type") == "operational_fault"]
    add(
        len(faults) == 0,
        f"idempotent path emits no operational_fault events ({len(faults)} found)",
        0, len(faults),
    )

    return results


def run_promote_full_tests():
    """Run the promote-full stage assertions.

    Exercises Promote-ToVerified.ps1 directly under the new 03b mock modes.
    Each path uses a fresh temp repo so state is isolated.

      1. pr_success (success path): full happy flow, audit + JSONL evidence
      2. push_fail (push failure): synthetic push failure, rollback verified
      3. pr_fail (PR-creation failure after push): rollback + branch deletion
      4. existing_open_pr (idempotent re-run): short-circuit at Step 2

    Tree-match and tree-mismatch paths are deferred (need bare-repo fixture);
    the real push path is exercised by the live throwaway smoke test (Stage 8).

    Returns (results, skipped_reason_or_None).
    """
    pwsh_path = _check_pwsh_available()
    if pwsh_path is None:
        return [], (
            "pwsh (PowerShell 7+) not found on PATH. The promote-full stage "
            "requires pwsh; powershell.exe is intentionally not used."
        )

    if not PROMOTE_SCRIPT_PATH.exists():
        return [TestResult(
            "promote-full", "promote-full", False,
            f"Promote-ToVerified.ps1 not found: {PROMOTE_SCRIPT_PATH}",
            "script exists", "missing",
        )], None

    fixture_path = CORPUS_DIR / PROMOTE_LOCAL_FIXTURE_REL
    if not fixture_path.exists():
        return [TestResult(
            "promote-full", "promote-full", False,
            f"Fixture not found: {fixture_path}",
            "file exists", "missing",
        )], None

    all_results = []

    paths = [
        ("promote-full:success",     "pr_success",        _assert_full_success_path),
        ("promote-full:push-fail",   "push_fail",         _assert_full_push_fail_path),
        ("promote-full:pr-fail",     "pr_fail",           _assert_full_pr_fail_path),
        ("promote-full:idempotent",  "existing_open_pr",  _assert_full_idempotent_path),
    ]

    for label, mock_mode, assert_fn in paths:
        work_root = Path(tempfile.mkdtemp(prefix="llm-wiki-promote-full-"))
        try:
            repo = _setup_promote_local_repo(work_root, fixture_path)
            try:
                run_data = _run_promote(
                    pwsh_path, repo, work_root, dry_run=False,
                    env_overrides={"LLM_WIKI_GITEA_MOCK_MODE": mock_mode},
                )
            except subprocess.TimeoutExpired:
                all_results.append(TestResult(
                    label, "promote-full", False,
                    f"subprocess hung (timeout after {PROMOTE_TIMEOUT_SECONDS}s)",
                    "completes within timeout", "subprocess hung",
                ))
                continue
            all_results.extend(assert_fn(label, run_data))
        finally:
            _cleanup_promote_local_worktrees(work_root)
            try:
                shutil.rmtree(work_root, ignore_errors=False)
            except OSError as exc:
                print(f"WARNING: cleanup of {work_root} failed: {exc}",
                      file=sys.stderr)

    return all_results, None


def main():
    parser = argparse.ArgumentParser(
        description="Golden corpus test harness for LLM-Wiki pipeline"
    )
    parser.add_argument(
        "--stage",
        choices=["parser", "validator", "promote-local", "promote-full", "all"],
        default="all",
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
        integration_results, skipped_reason = run_integration_tests(
            integration_fixtures
        )
        if skipped_reason is not None:
            # pwsh missing: cannot run, but this is environmental rather than
            # a test failure. Add to unimplemented_stages so exit 3 fires
            # with an explicit reason rather than emitting a false-failure.
            print(f"  SKIPPED: {skipped_reason}")
            unimplemented_stages.append(
                "integration (skipped: pwsh unavailable)"
            )
        else:
            print(f"  provider: stub via LLM_WIKI_STUB_DECISION env override")
            print(f"  decisions exercised: approve, reject, escalate "
                  f"(+ approve repeat for determinism)")
            all_results.extend(integration_results)

    # --- Promote-local assertions (TD-002 part 1) ---
    if args.stage in ("promote-local", "all"):
        print(f"\n--- Promote-local Assertions "
              f"(Promote-ToVerified.ps1 in isolation) ---")
        promote_results, skipped_reason = run_promote_local_tests()
        if skipped_reason is not None:
            print(f"  SKIPPED: {skipped_reason}")
            unimplemented_stages.append(
                "promote-local (skipped: pwsh unavailable)"
            )
        else:
            print(f"  Gitea: mocked via LLM_WIKI_GITEA_MOCK_MODE=local_only")
            print(f"  paths exercised: dry-run, live (post-local-git throw), "
                  f"rerun (idempotent recovery via startup reconciliation)")
            all_results.extend(promote_results)

    # --- Promote-full assertions (TD-002 part 2 / Phase 1.9) ---
    if args.stage in ("promote-full", "all"):
        print(f"\n--- Promote-full Assertions "
              f"(end-to-end Promote-ToVerified.ps1 with new mock modes) ---")
        promote_full_results, skipped_reason = run_promote_full_tests()
        if skipped_reason is not None:
            print(f"  SKIPPED: {skipped_reason}")
            unimplemented_stages.append(
                "promote-full (skipped: pwsh unavailable)"
            )
        else:
            print(f"  Gitea: mocked via LLM_WIKI_GITEA_MOCK_MODE per path")
            print(f"  paths exercised: success (pr_success), push-fail "
                  f"(push_fail), pr-fail (pr_fail), idempotent "
                  f"(existing_open_pr)")
            all_results.extend(promote_full_results)

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
