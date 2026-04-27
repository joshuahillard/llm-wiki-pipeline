# Golden Corpus Manifest — Phase 0 Bootstrap

**Purpose:** Ground truth for the parity harness (Item 4f) and all model evaluation. Every file has one deterministic expected end state so the pipeline can be tested mechanically.

**Authoritative source:** `corpus_manifest.json` is the machine-checkable manifest. This markdown file is the human-readable companion. If they disagree, the JSON wins.

**Schema:** `golden_corpus_manifest.schema.json` defines the structure of the JSON manifest.

**Violation taxonomy:** `policy_engine/VIOLATION_TAXONOMY.md` defines the `rule_id` values used in `expected_policy_violations`.

**Naming convention:** `{BUCKET}-{NNN}-{short-description}.md`


## Approve Examples (Expected Decision: `approve`, Exit Code: 0)

| ID | File | What It Tests | Expected Violations |
|----|------|--------------|-------------------|
| A-001 | `approve/A-001-clean-article.md` | Baseline: clean frontmatter, complete sections, accurate content | None |
| A-002 | `approve/A-002-minimal-valid.md` | Floor test: minimum viable article (only source_id + title) | None |
| A-003 | `approve/A-003-unicode-content.md` | Unicode, tables, backticks, special chars in code blocks | None |
| A-004 | `approve/A-004-long-form-article.md` | Long-form (~1,400 words): distributed consensus deep dive | None |
| A-005 | `approve/A-005-vendor-specific-guidance.md` | Neutrality observation on otherwise useful vendor-specific guidance | NEUTRALITY-001 |
| A-006 | `approve/A-006-broken-markdown.md` | Broken markdown (unclosed code fence) on otherwise accurate content | FORMATTING-002 |
| A-007 | `approve/A-007-missing-critical-section.md` | API reference missing expected examples section | COMPLETENESS-004 |
| A-008 | `approve/A-008-missing-h1-heading.md` | DNS article with no H1 heading — closes FORMATTING-001 desert | FORMATTING-001 |
| A-009 | `approve/A-009-unsourced-performance-claim.md` | Connection pooling with unsourced "60-70%" claim — closes ACCURACY-004 non-escalation gap | ACCURACY-004 |
| A-010 | `approve/A-010-git-branching.md` | Clean approve — Git branching strategies (domain diversity) | None |
| A-011 | `approve/A-011-structured-logging.md` | Clean approve — structured logging practices (domain diversity) | None |


## Reject Examples (Expected Decision: `reject`, Exit Code: 1)

| ID | File | What It Tests | Expected Violations |
|----|------|--------------|-------------------|
| R-001 | `reject/R-001-factual-contradiction.md` | Every factual claim about TCP/UDP is inverted | ACCURACY-001, ACCURACY-005 |
| R-002 | `reject/R-002-incomplete-article.md` | TODO placeholders, stub content, three empty sections | COMPLETENESS-001, COMPLETENESS-002, COMPLETENESS-003 |
| R-003 | `reject/R-003-contains-credentials.md` | Hardcoded password and AWS keys (synthetic), internal hostnames | SECURITY-001, SECURITY-002 |
| R-004 | `reject/R-004-stale-content.md` | Python 2.7, easy_install, Atom — all EOL/deprecated | ACCURACY-002 |
| R-005 | `reject/R-005-contains-pii.md` | Synthetic employee PII embedded in operational content | SECURITY-003 |
| R-006 | `reject/R-006-todo-placeholders.md` | CI/CD guide with TODO placeholders and stub sections | COMPLETENESS-001, COMPLETENESS-003 |
| R-007 | `reject/R-007-wrong-status-codes.md` | HTTP status codes with every definition systematically wrong | ACCURACY-001, ACCURACY-005 |


## Escalate Examples (Expected Decision: `escalate`, Exit Code: 2)

| ID | File | What It Tests | Expected Violations |
|----|------|--------------|-------------------|
| E-001 | `escalate/E-001-needs-domain-review.md` | Unresolved cost/latency trade-off requiring domain expertise | None (ambiguity, not error) |
| E-002 | `escalate/E-002-ambiguous-claims.md` | Oversimplified claims that are defensible in narrow contexts but misleading | ACCURACY-003, ACCURACY-004 |
| E-003 | `escalate/E-003-borderline-quality.md` | Vendor-specific recommendations without alternatives | NEUTRALITY-001 |
| E-004 | `escalate/E-004-oversimplified-architecture.md` | Microservices migration with context-dependent oversimplification | ACCURACY-003, NEUTRALITY-001 |
| E-005 | `escalate/E-005-borderline-stale-tooling.md` | Node.js 18 LTS guide approaching EOL — borderline staleness | ACCURACY-002 |


## Adversarial Examples (Parser-Level or Pipeline-Level Tests)

### Parser Errors (Expected Exit Code: 4, Decision: null)

| ID | File | What It Tests | Expected Error |
|----|------|--------------|---------------|
| ADV-001 | `adversarial/ADV-001-missing-source-id.md` | Missing required field | "Missing required field: source_id" |
| ADV-002 | `adversarial/ADV-002-invalid-yaml.md` | Malformed YAML | "YAML parse error" |
| ADV-004 | `adversarial/ADV-004-oversized-source-id.md` | source_id > 36 chars | "source_id exceeds 36 characters" |
| ADV-005 | `adversarial/ADV-005-prompt-injection-source-id.md` | Prompt injection in source_id | "source_id exceeds 36 characters" |
| ADV-007 | `adversarial/ADV-007-no-frontmatter.md` | No --- delimiter | "No frontmatter delimiter" |
| ADV-008 | `adversarial/ADV-008-empty-file.md` | Zero-byte file | "File is empty" |
| ADV-011 | `adversarial/ADV-011-special-chars-source-id.md` | Underscores/dots in source_id | "does not match ^[a-zA-Z0-9-]{1,36}$" |
| ADV-021 | `adversarial/ADV-021-null-source-id.md` | YAML `null` literal for source_id | "source_id is null" |
| ADV-022 | `adversarial/ADV-022-multiline-source-id.md` | Multiline source_id via YAML block scalar (`\|`) | "does not match ^[a-zA-Z0-9-]{1,36}$" |

### Parser Succeeds, Validator Decides

| ID | File | What It Tests | Expected Decision | Expected Violations |
|----|------|--------------|------------------|-------------------|
| ADV-003 | `adversarial/ADV-003-utf8-bom.md` | UTF-8 BOM at file start | approve | None |
| ADV-006 | `adversarial/ADV-006-oversized-value.md` | Non-identity field truncated to 256 bytes | approve | None |
| ADV-009 | `adversarial/ADV-009-frontmatter-only.md` | Valid frontmatter, no body | reject | COMPLETENESS-002 |
| ADV-010 | `adversarial/ADV-010-numeric-source-id.md` | YAML types source_id as int, str() coercion | approve | None |
| ADV-012 | `adversarial/ADV-012-nested-delimiters.md` | --- delimiters in article body | approve | None |
| ADV-013 | `adversarial/ADV-013-body-injection.md` | Prompt injection in HTML comment; body is approvable HTTP lifecycle article | approve | None |
| ADV-020 | `adversarial/ADV-020-yaml-anchor-attack.md` | YAML anchor/alias expansion; safe_load handles safely, extra fields truncated | approve | None |
| ADV-023 | `adversarial/ADV-023-duplicate-source-id-keys.md` | Duplicate `source_id` keys; YAML last-value-wins, parser uses second value | approve | None |
| ADV-024 | `adversarial/ADV-024-subtle-pii-in-code.md` | PII/credentials embedded in code block examples (SSN, API key, password) | reject | SECURITY-001, SECURITY-002, SECURITY-003 |
| ADV-025 | `adversarial/ADV-025-sandwich-injection.md` | Prompt injection in HTML comment sandwiched between valid content; LLM must ignore | approve | None |
| ADV-026 | `adversarial/ADV-026-mixed-severity-cascade.md` | Good security guidance mixed with dangerous advice (privileged containers, Vault root token exposure) | escalate | ACCURACY-003, SECURITY-002 |

### LLM Response Parsing (Expected Exit Code: 0 or 3)

| ID | File | What It Tests | Expected Exit | Response Mode |
|----|------|--------------|--------------|---------------|
| ADV-015 | `adversarial/ADV-015-llm-markdown-wrapped.md` | Valid JSON wrapped in markdown code fences — validator strips fences | 0 (approve) | invalid_raw |
| ADV-016 | `adversarial/ADV-016-llm-missing-confidence.md` | LLM response missing required `confidence` field | 3 (SCHEMA_FAULT) | invalid_raw |
| ADV-017 | `adversarial/ADV-017-llm-invalid-decision.md` | LLM response with `decision: "maybe"` — not in enum | 3 (SCHEMA_FAULT) | invalid_raw |
| ADV-018 | `adversarial/ADV-018-llm-extra-fields.md` | LLM response with extra `internal_notes` field — `additionalProperties: false` | 3 (SCHEMA_FAULT) | invalid_raw |
| ADV-019 | `adversarial/ADV-019-llm-empty-response.md` | LLM returns empty string — JSON parse fails | 3 (SCHEMA_FAULT) | invalid_raw |

### Token Overflow (Expected Exit Code: 5, Decision: null)

| ID | File | What It Tests |
|----|------|--------------|
| ADV-014 | `adversarial/ADV-014-token-overflow.md` | ~1.1 MB glossary. Exceeds any context window. EXIT_TOKEN_OVERFLOW before API call. |


## Integration Tests

| ID | File | What It Tests | Procedure |
|----|------|--------------|-----------|
| CTX-001 | `integration/CTX-001-digest-change-test.md` | End-to-end orchestration: parse -> validate -> ledger write -> audit -> F7 promotion gate. Exercises approve / reject / escalate paths via `LLM_WIKI_STUB_DECISION` env override, plus a determinism check (approve repeated). Implemented as the `integration` stage in `run_harness.py` (Phase 1.7). | Automated — runs on `python run_harness.py --stage all`. Requires pwsh (PowerShell 7+) on PATH; stage is skipped with explicit reason if pwsh is missing. The `integration/CTX-001-README.md` is preserved as a Phase 0.6 historical artifact; its digest-rotation premise is moot under current code (no caching layer to invalidate, ledger writes are append-only via timestamped filenames). |

## Promote-local Tests (TD-002 part 1)

Exercises `Promote-ToVerified.ps1` directly (not via `Run-Validator.ps1`) to verify the local-git half of TD-002: temp-worktree creation, article copy from `provisional/` to `verified/`, commit on a deterministic branch alias, audit-preview field population (`local_commit_sha`, `worktree_path`), and JSONL fault emission on rollback. Reuses `approve/A-001-clean-article.md` as input — no new fixture files.

| Path | What It Tests |
|------|--------------|
| dry-run | `-DryRun` produces audit preview with new `local_commit_sha`/`worktree_path` keys (null in dry-run); no JSONL faults |
| live (mocked Gitea) | Worktree created in `%TEMP%\llm-wiki-promote-<guid>`, article copied, commit on `auto/<source>/<8-hex>`, post-local-git throw fires with `promotion_gated_pending_remote_wiring` |
| rerun (idempotent recovery) | Phase 1.9: orphan worktree from the prior run is auto-cleaned by `Invoke-StartupReconciliation`, then a fresh local-git promotion runs and throws again at the `local_only` post-local-git boundary. (Pre-Phase-1.9 contract was "fail loudly with branch already exists.") |

Live Gitea calls are mocked via `LLM_WIKI_GITEA_MOCK_MODE=local_only` (test-only env var; `Invoke-GiteaApi` returns canned "no remote PR / branch not found" responses). Implemented as the `promote-local` stage in `run_harness.py`. 31 assertions; runs on `python run_harness.py --stage all` and `--stage promote-local`. Requires pwsh; skipped with explicit reason if pwsh is missing.

## Promote-full Tests (TD-002 part 2)

Exercises the FULL `Promote-ToVerified.ps1` flow under the new mock modes introduced in Phase 1.9 / 03b. Each path uses a fresh temp repo (via `_setup_promote_local_repo`), a unique `LLM_WIKI_GITEA_MOCK_MODE` setting, and asserts on structured JSONL events (no string-substring couplings beyond a few diagnostic message checks).

| Path | Mock Mode | What It Tests |
|------|-----------|--------------|
| success | `pr_success` | Full happy flow: local-git → push (mocked-skipped) → PR creation (canned success) → pending_pr write → audit rewrite → `promotion_completed` JSONL with all 5 structured fields. Audit file populated with `pr_number=1` and a non-empty `pr_url`. No `operational_fault` events emitted. |
| push-fail | `push_fail` | Synthetic push failure inside `Invoke-GitPushPromotion`. Verifies rollback: worktree + local branch removed, `PROMOTION_PUSH_FAILED` JSONL fault emitted with `step=git_push_promotion`, no `promotion_completed` event. |
| pr-fail-after-push | `pr_fail` | PR creation API returns 422 after push success. Verifies rollback: `Remove-GiteaBranch` called (mock returns 204), worktree + local branch removed, `PROMOTION_PR_FAILED` JSONL fault emitted with `step=pr_creation`. `promotion_push_completed` event present (push fired before PR fail); no `promotion_completed` event. |
| idempotent | `existing_open_pr` | Branch + open PR both exist on remote (mocked). Verifies the Step-2 short-circuit: exit 0, "Existing open PR #1 found ... idempotent re-run path" message, no new push, no new PR creation, no `promotion_completed` event, no faults. |

Tree-equivalence paths (orphan-branch recovery: tree-match, tree-mismatch) are deferred to a future phase — they need a bare-repo fixture (real `git fetch` against a local file:// remote) to exercise the production `Test-RemoteTreeEquivalence` function. The real `git push` path is exercised by the live throwaway-Gitea smoke test (Phase 1.9 ledger entry), not by an automated test stage.

Implemented as the `promote-full` stage in `run_harness.py`. 30 assertions; runs on `python run_harness.py --stage all` and `--stage promote-full`. Requires pwsh.


## Coverage Summary

### By decision (non-adversarial buckets only)

| Category | Count | IDs |
|----------|-------|-----|
| Approve (approve/) | 11 | A-001 – A-011 |
| Reject (reject/) | 7 | R-001 – R-007 |
| Escalate (escalate/) | 5 | E-001 – E-005 |

### By decision (all fixtures including adversarial)

| Category | Count | IDs |
|----------|-------|-----|
| Approve decisions | 16 | A-001 – A-011, ADV-003, ADV-006, ADV-010, ADV-012, ADV-013, ADV-015, ADV-020, ADV-023, ADV-025 |
| Reject decisions | 9 | R-001 – R-007, ADV-009, ADV-024 |
| Escalate decisions | 6 | E-001 – E-005, ADV-026 |
| Schema fault (exit 3) | 4 | ADV-016, ADV-017, ADV-018, ADV-019 |
| Parser errors (exit 4) | 9 | ADV-001, ADV-002, ADV-004, ADV-005, ADV-007, ADV-008, ADV-011, ADV-021, ADV-022 |
| Token overflow (exit 5) | 1 | ADV-014 |
| Integration tests | 1 | CTX-001 |
| **Total fixtures** | **50** | |
| **Adversarial ratio** | **52.0%** | 26 adversarial / 50 total |

### Violation IDs Exercised

ACCURACY-001, ACCURACY-002, ACCURACY-003, ACCURACY-004, ACCURACY-005, COMPLETENESS-001, COMPLETENESS-002, COMPLETENESS-003, COMPLETENESS-004, FORMATTING-001, FORMATTING-002, NEUTRALITY-001, SECURITY-001, SECURITY-002, SECURITY-003

### Not Yet Exercised

All 15 violation rule IDs in the taxonomy are now exercised by at least one fixture.
