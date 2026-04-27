"""
validator_runner.py — Production LLM content evaluator for LLM-Wiki pipeline.

This is the runtime validator module that the orchestration layer should call.
The test harness may wrap or import this file, but production behavior lives
here.

Usage:
    python validator_runner.py <article_path> [--config path/to/validator_config.json]

Exit codes:
    0 — APPROVE
    1 — REJECT
    2 — ESCALATE
    3 — SCHEMA_FAULT
    4 — SYSTEM_FAULT
    5 — TOKEN_OVERFLOW
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PARSER_PATH = SCRIPT_DIR / "parse_identity.py"
CONFIG_PATH = SCRIPT_DIR / "ops" / "validator_config.json"
TAXONOMY_PATH = SCRIPT_DIR / "policy_engine" / "VIOLATION_TAXONOMY.md"
SYSTEM_PROMPT_PATH = SCRIPT_DIR / "SYSTEM_PROMPT.md"
SCHEMA_HELPERS_PATH = SCRIPT_DIR / "schema_helpers.py"


def _load_schema_helpers():
    spec = importlib.util.spec_from_file_location(
        "_pipeline_schema_helpers",
        str(SCHEMA_HELPERS_PATH),
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load schema helpers from {SCHEMA_HELPERS_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_schema_helpers = _load_schema_helpers()
SchemaError = _schema_helpers.SchemaError
load_schema = _schema_helpers.load_schema
validate = _schema_helpers.validate


EXIT_APPROVE = 0
EXIT_REJECT = 1
EXIT_ESCALATE = 2
EXIT_SCHEMA_FAULT = 3
EXIT_SYSTEM_FAULT = 4
EXIT_TOKEN_OVERFLOW = 5

DECISION_EXIT_MAP = {
    "approve": EXIT_APPROVE,
    "reject": EXIT_REJECT,
    "escalate": EXIT_ESCALATE,
}

BYTES_PER_TOKEN_ESTIMATE = 4  # Conservative fallback; used only when model-specific tokenizer is unavailable
SYSTEM_OVERHEAD_TOKENS = 4096
RESPONSE_RESERVE_TOKENS = 2048  # Strategy Kit 7.2 recommended reserve for response
PARSER_TIMEOUT_SECONDS = 30
LLM_TIMEOUT_SECONDS = 120
LLM_MAX_OUTPUT_TOKENS = 4096
LLM_RETRY_ATTEMPTS = 1
LLM_RETRY_DELAY_SECONDS = 2
TOKEN_COUNT_TIMEOUT_SECONDS = 30


class ValidatorError(Exception):
    """Base exception for validator_runner errors."""
    pass


class ConfigError(ValidatorError):
    """Missing or invalid configuration."""
    pass


class ParserError(ValidatorError):
    """parse_identity.py failed to run or returned invalid output."""
    pass


class ProviderError(ValidatorError):
    """Provider dispatch failure."""
    pass


def default_provider(payload, config):
    """Default provider dispatch based on validator_config.json 'provider'.

    Supported providers:
        stub       — deterministic canned response for testing (no LLM call)
        anthropic  — Anthropic Messages API (requires ANTHROPIC_API_KEY)
        vertex_ai  — Vertex AI / Gemini (not yet implemented)
    """
    provider = config.get("provider", "stub")

    if provider == "stub":
        return _stub_response()

    if provider == "anthropic":
        return _anthropic_provider(payload, config)

    if provider == "vertex_ai":
        raise ProviderError(
            "Vertex AI provider integration pending. "
            "Use provider='stub' or provider='anthropic'."
        )

    raise ConfigError(f"Unknown provider: {provider}")


def _stub_response():
    """Fallback stub - returns a minimal canned response. Only for smoke tests.

    Decision defaults to "approve" but can be overridden via the
    LLM_WIKI_STUB_DECISION env var (one of "approve", "reject", "escalate")
    so end-to-end orchestration tests can exercise reject/escalate paths
    without a live provider. Unknown values fall back to "approve".
    """
    decision = os.environ.get("LLM_WIKI_STUB_DECISION", "approve").lower()
    if decision == "reject":
        return json.dumps({
            "decision": "reject",
            "confidence": 0.9,
            "reasoning": "Stub reject response - no LLM call was made.",
            "policy_violations": [
                {
                    "rule_id": "ACCURACY-001",
                    "description": "Stub-injected violation for orchestration testing.",
                    "severity": "critical",
                },
            ],
            "recommendations": [
                "Connect a real LLM provider for actual evaluation.",
            ],
        })
    if decision == "escalate":
        return json.dumps({
            "decision": "escalate",
            "confidence": 0.6,
            "reasoning": "Stub escalate response - no LLM call was made.",
            "policy_violations": [
                {
                    "rule_id": "NEUTRALITY-001",
                    "description": "Stub-injected escalation signal for orchestration testing.",
                    "severity": "minor",
                },
            ],
            "recommendations": [
                "Connect a real LLM provider for actual evaluation.",
            ],
        })
    return json.dumps({
        "decision": "approve",
        "confidence": 0.5,
        "reasoning": "Stub response - no LLM call was made.",
        "policy_violations": [],
        "recommendations": [
            "Connect a real LLM provider for actual evaluation.",
        ],
    })


def _anthropic_provider(payload, config):
    """Call the Anthropic Messages API and return the raw response text.

    Auth: reads ANTHROPIC_API_KEY from the environment (standard SDK
    behavior).  Raises ProviderError if the key is missing or the API
    call fails after retries.

    Retry policy: one retry on transient errors (rate limit, overload,
    connection).  No retry on authentication or bad-request errors.
    """
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderError(
            "The 'anthropic' package is required for provider='anthropic'. "
            "Install it with: pip install anthropic"
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ProviderError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Required for provider='anthropic'."
        )

    model_id = config.get("model_id", "claude-sonnet-4-6")
    temperature = config.get("temperature", 0.0)
    top_p = config.get("top_p", 1.0)

    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=LLM_TIMEOUT_SECONDS,
    )

    last_error = None
    for attempt in range(1 + LLM_RETRY_ATTEMPTS):
        try:
            request_args = {
                "model": model_id,
                "max_tokens": LLM_MAX_OUTPUT_TOKENS,
                "system": payload["system"],
                "messages": [{"role": "user", "content": payload["user"]}],
            }

            # Anthropic rejects requests that specify both sampling controls
            # for this model. Prefer temperature for deterministic evaluation.
            if temperature is not None:
                request_args["temperature"] = temperature
            elif top_p is not None:
                request_args["top_p"] = top_p

            message = client.messages.create(**request_args)

            # Extract text from the response content blocks.
            text_parts = []
            for block in message.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)

            if not text_parts:
                raise ProviderError(
                    "Anthropic response contained no text content blocks."
                )

            return "\n".join(text_parts)

        except anthropic.AuthenticationError as exc:
            # Do not retry auth failures.
            raise ProviderError(
                f"Anthropic authentication failed: {exc}"
            ) from exc

        except anthropic.BadRequestError as exc:
            # Do not retry bad requests (malformed payload).
            raise ProviderError(
                f"Anthropic bad request: {exc}"
            ) from exc

        except (
            anthropic.RateLimitError,
            anthropic.InternalServerError,
            anthropic.APIConnectionError,
        ) as exc:
            last_error = exc
            if attempt < LLM_RETRY_ATTEMPTS:
                print(
                    f"WARNING: Anthropic transient error (attempt "
                    f"{attempt + 1}/{1 + LLM_RETRY_ATTEMPTS}): {exc}",
                    file=sys.stderr,
                )
                time.sleep(LLM_RETRY_DELAY_SECONDS)
                continue
            # Exhausted retries.
            raise ProviderError(
                f"Anthropic API failed after {1 + LLM_RETRY_ATTEMPTS} "
                f"attempt(s): {last_error}"
            ) from last_error

        except anthropic.APIError as exc:
            # Catch-all for unexpected API errors. Do not retry.
            raise ProviderError(
                f"Anthropic API error: {exc}"
            ) from exc

    # Should not reach here, but guard against logic errors.
    raise ProviderError(
        f"Anthropic provider exhausted all attempts: {last_error}"
    )


def load_config(config_path=None):
    """Load validator_config.json and return a dict."""
    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.exists():
        raise ConfigError(f"Config not found: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ConfigError(f"Config is not valid JSON: {exc}") from exc

    if not isinstance(config, dict):
        raise ConfigError("Config root must be a JSON object")

    return config


def load_text_file(path, label):
    """Read a UTF-8 text file."""
    if not path.exists():
        raise ConfigError(f"{label} not found: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"Failed to read {label}: {exc}") from exc


def run_parser(article_path, repo_root=None):
    """Run parse_identity.py and return (exit_code, parsed_json, body_text)."""
    cmd = [sys.executable, str(PARSER_PATH), str(article_path)]
    if repo_root is not None:
        cmd.extend(["--repo-root", str(repo_root)])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=PARSER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ParserError(
            f"Parser timed out after {PARSER_TIMEOUT_SECONDS}s"
        ) from exc
    except FileNotFoundError as exc:
        raise ParserError(f"Parser not found: {exc}") from exc

    try:
        parsed = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise ParserError(
            f"Parser stdout is not valid JSON: {proc.stdout[:200]}"
        ) from exc

    if proc.returncode != 0:
        return proc.returncode, parsed, None

    body = _extract_body(article_path)
    return 0, parsed, body


def _extract_body(article_path):
    """Read article and return text after the closing frontmatter delimiter."""
    try:
        with open(article_path, encoding="utf-8-sig") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise ParserError(
            f"Failed to read article for body extraction: {exc}"
        ) from exc

    lines = content.split("\n")
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break

    if closing is None:
        return ""

    return "\n".join(lines[closing + 1:])


def estimate_tokens_by_bytes(text):
    """Estimate token count conservatively from UTF-8 byte length.

    This is the fallback used when the model-specific tokenizer is
    unavailable (stub provider, missing SDK, or API error).  The
    4-bytes-per-token ratio is intentionally conservative — it will
    overcount, which is safe (it triggers TOKEN_OVERFLOW for borderline
    articles rather than letting them through and failing mid-request).
    """
    return len(text.encode("utf-8")) // BYTES_PER_TOKEN_ESTIMATE


def count_tokens_anthropic(system_text, user_text, model_id):
    """Use the Anthropic Messages API count_tokens endpoint.

    Returns the exact input token count for the given payload under the
    model's tokenizer.  Raises ProviderError if the call fails.
    """
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderError(
            "anthropic package required for model-specific token counting"
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ProviderError(
            "ANTHROPIC_API_KEY not set; cannot use Anthropic tokenizer"
        )

    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=TOKEN_COUNT_TIMEOUT_SECONDS,
    )

    try:
        result = client.messages.count_tokens(
            model=model_id,
            system=system_text,
            messages=[{"role": "user", "content": user_text}],
        )
        return result.input_tokens
    except Exception as exc:
        raise ProviderError(
            f"Anthropic count_tokens failed: {exc}"
        ) from exc


def count_tokens_for_provider(system_text, user_text, config):
    """Dispatch to the model-specific tokenizer, with byte-estimate fallback.

    Returns (token_count, method_used) where method_used is one of:
        "anthropic_api"  — exact count from Anthropic count_tokens endpoint
        "byte_estimate"  — conservative fallback (4 bytes per token)

    The fallback is used when:
        - provider is 'stub' (no API to call)
        - anthropic SDK is not installed
        - ANTHROPIC_API_KEY is not set
        - the count_tokens API call fails for any reason
    """
    provider = config.get("provider", "stub")
    model_id = config.get("model_id", "claude-sonnet-4-6")

    if provider == "anthropic":
        try:
            count = count_tokens_anthropic(system_text, user_text, model_id)
            return count, "anthropic_api"
        except (ProviderError, Exception) as exc:
            print(
                f"WARNING: Model-specific token count failed, falling back "
                f"to byte estimate: {exc}",
                file=sys.stderr,
            )

    # Fallback: conservative byte-based estimate
    total_text = (system_text or "") + (user_text or "")
    count = estimate_tokens_by_bytes(total_text) + SYSTEM_OVERHEAD_TOKENS
    return count, "byte_estimate"


def check_token_budget(payload, config):
    """Return (fits, token_info) where fits is True if the payload fits
    within the configured context window minus the response reserve.

    payload must be the dict returned by build_llm_payload() so the
    budget check counts the exact system and user strings that will
    be sent to the provider.

    token_info is a dict with:
        input_tokens   — counted or estimated input token total
        max_tokens     — configured context window
        budget         — max_tokens minus response reserve
        method         — "anthropic_api" or "byte_estimate"
    """
    max_tokens = config.get("max_context_tokens", 128000)
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ConfigError(
            f"max_context_tokens must be a positive integer, got {max_tokens!r}"
        )

    budget = max_tokens - RESPONSE_RESERVE_TOKENS

    input_tokens, method = count_tokens_for_provider(
        payload["system"], payload["user"], config
    )

    token_info = {
        "input_tokens": input_tokens,
        "max_tokens": max_tokens,
        "budget": budget,
        "method": method,
    }

    return input_tokens <= budget, token_info


def build_llm_payload(source_id, frontmatter, body, system_prompt, taxonomy):
    """Assemble the prompt payload for the LLM."""
    system_text = system_prompt.strip()
    if taxonomy:
        system_text += "\n\n---\n\n" + taxonomy.strip()

    frontmatter_block = json.dumps(frontmatter, indent=2, ensure_ascii=False)

    user_text = (
        f"## Article Metadata\n"
        f"source_id: {source_id}\n"
        f"frontmatter:\n```json\n{frontmatter_block}\n```\n\n"
        f"## Article Body\n\n{body}"
    )

    return {"system": system_text, "user": user_text}


def parse_llm_response(raw_response):
    """Parse raw LLM response text into a dict."""
    if not isinstance(raw_response, str):
        return None

    text = raw_response.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def run(article_path, config_path=None, config=None, provider=None,
        system_prompt=None, taxonomy=None, repo_root=None):
    """Full evaluation pipeline. Returns (exit_code, result_dict_or_none)."""
    if provider is None:
        provider = default_provider

    if config is None:
        config = load_config(config_path)
    elif not isinstance(config, dict):
        raise ConfigError("config must be a dict when provided")

    parser_exit, parsed, body = run_parser(article_path, repo_root=repo_root)
    if parser_exit != 0:
        return EXIT_SYSTEM_FAULT, None

    source_id = parsed.get("source_id")
    frontmatter = parsed.get("frontmatter", {})

    if system_prompt is None:
        system_prompt = (
            load_text_file(SYSTEM_PROMPT_PATH, "SYSTEM_PROMPT.md")
            if SYSTEM_PROMPT_PATH.exists() else ""
        )

    if taxonomy is None:
        taxonomy = (
            load_text_file(TAXONOMY_PATH, "VIOLATION_TAXONOMY.md")
            if TAXONOMY_PATH.exists() else ""
        )

    payload = build_llm_payload(
        source_id, frontmatter, body or "", system_prompt, taxonomy
    )

    if body is not None:
        fits, token_info = check_token_budget(payload, config)
        if not fits:
            print(
                f"TOKEN_OVERFLOW: {token_info['input_tokens']} input tokens "
                f"exceeds budget of {token_info['budget']} "
                f"(max_context={token_info['max_tokens']}, "
                f"reserve={RESPONSE_RESERVE_TOKENS}, "
                f"method={token_info['method']})",
                file=sys.stderr,
            )
            return EXIT_TOKEN_OVERFLOW, None

    try:
        raw_response = provider(payload, config)
    except ValidatorError:
        raise
    except Exception as exc:
        raise ProviderError(
            f"Provider callable raised {type(exc).__name__}: {exc}"
        ) from exc

    result_dict = parse_llm_response(raw_response)
    if result_dict is None:
        print(
            f"ERROR: LLM response is not parseable JSON: {str(raw_response)[:300]}",
            file=sys.stderr,
        )
        return EXIT_SCHEMA_FAULT, None

    schema = load_schema()
    schema_errors = validate(result_dict, schema)
    if schema_errors:
        print(
            f"ERROR: LLM output has {len(schema_errors)} schema violation(s):",
            file=sys.stderr,
        )
        for path_str, message in schema_errors:
            print(f"  [{path_str}] {message}", file=sys.stderr)
        return EXIT_SCHEMA_FAULT, None

    decision = result_dict.get("decision", "")
    exit_code = DECISION_EXIT_MAP.get(decision, EXIT_SCHEMA_FAULT)
    return exit_code, result_dict


def main(argv=None):
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="LLM content evaluator for LLM-Wiki pipeline"
    )
    parser.add_argument(
        "article",
        type=str,
        help="Path to the article markdown file",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to validator_config.json "
             "(default: pipeline/ops/validator_config.json)",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Absolute path to the repository root. Forwarded to "
             "parse_identity.py for deterministic repo-relative identity.",
    )
    args = parser.parse_args(argv)

    try:
        exit_code, result_dict = run(
            args.article, config_path=args.config, repo_root=args.repo_root
        )
    except (ValidatorError, SchemaError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(EXIT_SYSTEM_FAULT)

    if result_dict is not None:
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()