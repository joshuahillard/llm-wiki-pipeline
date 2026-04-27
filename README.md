# LLM-Wiki Content Pipeline

Automated content validation pipeline for wiki articles using LLM-based evaluation, PR-gated promotion, externalized state, and a documentation spine for trust, governance, and program management.

The pipeline takes draft articles in `pipeline/provisional/`, evaluates them against a structured policy bundle using an LLM, writes ledger and audit records to an out-of-tree state directory, and (when fully wired) gates promotion to `pipeline/verified/` behind a Gitea pull request.

## Status

**Current phase:** Phase 1.9 (per `PROJECT_LEDGER.md`, last updated April 27, 2026)

| Area | State |
|------|-------|
| Parser harness | 59 / 59 assertions passing |
| Validator harness | 225 / 225 assertions passing |
| Integration harness | 83 / 83 assertions passing (approve / reject / escalate decision paths + determinism check; F7 allowlist inverted Phase 1.9) |
| Promote-local harness | 31 / 31 assertions passing (TD-002 part 1 boundary tests) |
| Promote-full harness | 30 / 30 assertions passing (TD-002 part 2 — success / push-fail / PR-fail-after-push / idempotent-rerun paths) |
| Combined `--stage all` | 387 / 387 passing, 0 failing, **exit 0** |
| Golden corpus fixtures | 50 (52% adversarial ratio) |
| LLM provider | Anthropic Claude Sonnet 4.6 — wired in `pipeline/validator_runner.py`, **smoke-tested live in Phase 1.6** (decision=`approve`, confidence `0.91`, ~8.2s end-to-end) |
| Promotion path | **Fully wired (Phase 1.9):** local-git → push → PR creation → audit → JSONL `promotion_completed` event. Tree-SHA equivalence (P0-8) implemented as Option B (git fetch + rev-parse). Live-smoke-tested 2026-04-27 against an external throwaway Gitea (clean publish + idempotent re-run). |

### Technical Debt Register (summary)

See `PROJECT_LEDGER.md` § Technical Debt Register for full detail.

| ID | Status | Note |
|----|--------|------|
| TD-001 | **Closed** (Phase 1.5) | Model-specific tokenizer wired via Anthropic `count_tokens` API, with byte-estimate fallback |
| TD-002 | **Closed** (Phase 1.9) | Live push + PR creation + tree-SHA equivalence (P0-8) all wired; live-smoke-tested against an external throwaway Gitea |
| TD-003 | **Closed** (Phase 1.0) | Deterministic repo-root-relative identity in `parse_identity.py` |
| TD-004 | Open | Documentation alignment across portfolio entry points |

## Folder Structure

```text
LLM Model/
  README.md                        # This file
  PROJECT_LEDGER.md                # Canonical timeline and decision log
  PERSONA_LIBRARY.md               # Component-level responsibility map
  PROMPT_ARCHITECTURE.md           # Prompt design conventions
  RUNTIME_PROMPTS.md               # Operational runbook prompts
  design-docs/                     # Architecture and hardening narratives
  Foundations/                     # Trust, schema, auditability, corpus design
  Governance/                      # Human-in-the-loop governance contract
  Program-Management/              # Delivery and control-plane discipline
  LLM/                             # LLM-focused research and reference notes
  strategy/                        # Strategy kit and production-readiness specs
  pipeline/                        # Runtime scripts, schema, policy bundle, tests
    requirements.txt
    Run-Validator.ps1              # Orchestration entry point
    Promote-ToVerified.ps1         # Promotion preflight and (gated) PR creation
    validator_runner.py            # Production LLM evaluator
    parse_identity.py              # Single-parser frontmatter / identity extraction
    schema_helpers.py              # Schema loading and validation
    validation_result.schema.json  # JSON Schema for validator output
    SYSTEM_PROMPT.md               # Validator system prompt
    ops/
      validator_config.json        # Provider, model, temperature, context budget
    policy_engine/
      VIOLATION_TAXONOMY.md
      _policy_bundle.md
    provisional/                   # Drafts awaiting validation
    verified/                      # Articles approved through the pipeline
    tests/
      run_harness.py               # Golden corpus test harness
      golden_corpus/               # Fixtures (approve / reject / escalate / adversarial)
  llm-wiki-state/                  # Dev mirror of out-of-tree runtime state (logs/, ledger/, audit/)
```

## Pipeline Runtime State

At runtime, the pipeline expects external state at `C:\llm-wiki-state\` (Windows-first design — see `pipeline/Run-Validator.ps1` `-StateRoot` parameter to override). The in-tree `llm-wiki-state/` directory mirrors that structure for development and testing; runtime contents (logs, ledger entries, audit JSON) are gitignored.

## Install

Requirements:

- **Python 3.10+** (the Anthropic SDK and `jsonschema` require modern Python)
- **PowerShell 7+ (`pwsh`)** is required for the integration stage of the test harness. `Run-Validator.ps1` and `Promote-ToVerified.ps1` themselves now also parse cleanly under Windows PowerShell 5.1 (em-dashes were replaced with ASCII hyphens in Phase 1.7), but the integration stage hard-requires `pwsh` and skips with an explicit reason if it is unavailable.
- An **Anthropic API key** in `ANTHROPIC_API_KEY` (only required to use the live provider; the test harness uses a deterministic stub)

Install Python dependencies:

```bash
pip install -r pipeline/requirements.txt
```

Or install individually:

```bash
pip install "anthropic>=0.40" "jsonschema>=4.0" "pyyaml>=6.0"
```

## Test

The golden corpus harness verifies parser, validator, and orchestration behavior against 50 fixtures across `approve` / `reject` / `escalate` / `adversarial` / `integration` categories.

Run the parser stage (frontmatter parsing only, 59 assertions):

```bash
python pipeline/tests/run_harness.py --stage parser
```

Run the validator stage (full evaluation against deterministic stub responses, 225 assertions):

```bash
python pipeline/tests/run_harness.py --stage validator
```

Run all stages (parser + validator + integration, 320 assertions):

```bash
python pipeline/tests/run_harness.py --stage all
```

Expected output for `--stage all`: **`320 passed, 0 failed`** with **exit code 0**. The integration stage exercises the full orchestration end-to-end — parse, validate, ledger write, audit, and the F7 promotion gate — across approve / reject / escalate decision paths plus a determinism re-run, using the deterministic stub provider with decisions controlled by the `LLM_WIKI_STUB_DECISION` env var.

The integration stage hard-requires `pwsh` (PowerShell 7+) on the PATH. If `pwsh` is missing, the stage is skipped with an explicit reason and the harness exits 3 (partial coverage) rather than failing. `powershell.exe` (5.1) is intentionally not used as a fallback even if available.

## Run the validator (live provider)

Set your API key and invoke the orchestration script. Drop draft articles into `pipeline/provisional/`:

```powershell
$env:ANTHROPIC_API_KEY = "your-key-here"
.\pipeline\Run-Validator.ps1 -DryRun
```

Without `ANTHROPIC_API_KEY` set, the orchestration script prints a warning and falls back to the deterministic stub provider — useful for smoke-testing the orchestration path without API costs, but **the stub returns approve for every article**, so do not interpret stub-mode results as semantic validation.

## Key Documents

- **`PROJECT_LEDGER.md`** — canonical timeline, decision log, and Technical Debt Register
- **`strategy/LLM-Wiki_Strategy_Kit.md`** — primary planning artifact (architecture, FMEA, ADRs, OQ tracking)
- **`Foundations/`** — trust model, schema validation, transaction identity, trust boundaries, golden corpus design
- **`Governance/Human-in-the-Loop Governance.md`** — governance contract and the seven invariants
- **`pipeline/SYSTEM_PROMPT.md`** + **`pipeline/policy_engine/_policy_bundle.md`** — what the validator actually evaluates against

## External / Private Working Material

Some artifacts referenced in the project ledger are working material maintained outside this repository and are **not included** in the public source tree:

- The 77-source machine-readable academic bibliography described in PROJECT_LEDGER Phase 0.10 lives in a private research vault and is not included in this repository. The smaller curated `LLM/Academic Source Map - LLM, Coding, and Governance.md` *is* in the repo and represents the public-facing academic anchor list.
- The Gitea instance referenced by `pipeline/Promote-ToVerified.ps1` for the promotion path is configured externally; credentials are read from environment variables (`GITEA_URL`, `GITEA_TOKEN`, `GITEA_REPO_OWNER`, `GITEA_REPO_NAME`) and are not stored in this repository.

## Roadmap (next engineering steps)

The remaining work is grouped into three small follow-up phases, sequenced by risk-to-leave-undone. The intent is to keep technical debt minimal: each phase closes a specific gap surfaced by the Phase 1.9 Limitations review or carried forward from earlier phases.

### Phase 2.0 — Tree-equivalence test coverage (HIGH priority; medium effort)

**Why now:** `Test-RemoteTreeEquivalence` is in production from Phase 1.9 but has zero automated test coverage. A regression could ship green and only surface in the rare orphan-recovery scenario; this is the highest-risk untested code path in the pipeline.

1. **Bare-repo fixture for `promote-full`** — set up a local `file://` remote in a temp dir so the real `git fetch` runs against controlled tree state.
2. **Add `tree_match` and `tree_mismatch` paths to the `promote-full` stage** — exercise the recovery branch (skip push, create PR) and the fail-closed branch (rollback worktree, throw with P0-8 violation) of `Test-RemoteTreeEquivalence`.
3. **Live orphan-recovery smoke test** — manual one-off against a throwaway Gitea repo: delete an existing PR, leave the branch, re-run the pipeline, verify the equivalence check fires correctly and either recovers or fails closed as expected. Same throwaway-repo flow used in Phase 1.9.

### Phase 2.1 — CI safety nets + tokenizer evidence (MEDIUM priority; small effort)

**Why now:** All three add observability without changing pipeline behavior. They make latent issues (Gitea API drift, tokenizer-method ambiguity) visible at CI time instead of in production.

4. **CI-time mock-vs-real parity assertion** — load `pipeline/tests/fixtures/gitea_pr_response_shape.json` and (when configured) query a throwaway Gitea to verify the consumer-required subset is still present. Catches Gitea API breaking changes before they hit production.
5. **`article_token_count` threading into ledger entries** — the count is computed exactly in `validator_runner.py` via Anthropic `count_tokens` but is not currently passed back to the PowerShell orchestration layer for ledger inclusion. Phase 1.6 follow-up.
6. **Positive `INFO: token_method=...` log line on every run** — currently the live-tokenizer path's success is inferred from the absence of a fallback warning. A positive log line provides direct evidence symmetry. Phase 1.6 follow-up.

### Phase 2.2 — Documentation alignment / TD-004 (LOW priority; small-medium effort)

**Why last:** Closes the final tracked tech debt item. Best done after the prior phases land any doc-shape changes (test counts, file locations, function names) so the audit happens against a stable target.

7. **README + portfolio doc audit** across all entry points (README, Foundations/, Governance/, Program-Management/, Strategy Kit) to fully close TD-004.

### Long-tail (tracked separately, not in any specific phase)

- No LICENSE/CI/dependency manifest historically; `requirements.txt` was added at the public-push milestone (Phase 1.5).
