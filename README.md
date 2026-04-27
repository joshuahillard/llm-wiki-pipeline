# LLM-Wiki Content Pipeline

Automated content validation pipeline for wiki articles using LLM-based evaluation, PR-gated promotion, externalized state, and a documentation spine for trust, governance, and program management.

The pipeline takes draft articles in `pipeline/provisional/`, evaluates them against a structured policy bundle using an LLM, writes ledger and audit records to an out-of-tree state directory, and (when fully wired) gates promotion to `pipeline/verified/` behind a Gitea pull request.

## Status

**Current phase:** Phase 1.5 (per `PROJECT_LEDGER.md`, last updated April 9, 2026)

| Area | State |
|------|-------|
| Parser harness | 59 / 59 assertions passing |
| Validator harness | 225 / 225 assertions passing |
| Combined (deduplicated) | 244 / 244 passing, 0 failing |
| Integration test stage | **Intentionally unimplemented** — exit code 3 from `--stage all` reflects partial coverage, not a failure |
| Golden corpus fixtures | 50 (52% adversarial ratio) |
| LLM provider | Anthropic Claude Sonnet 4.6 — wired in `pipeline/validator_runner.py`, **not yet smoke-tested against a real article** |
| Promotion path | Scaffolded with Gitea client, declined-PR reconciliation, and branch-existence check; **gated behind a hard fail until git-push wiring lands (TD-002)** |

### Technical Debt Register (summary)

See `PROJECT_LEDGER.md` § Technical Debt Register for full detail.

| ID | Status | Note |
|----|--------|------|
| TD-001 | **Closed** (Phase 1.5) | Model-specific tokenizer wired via Anthropic `count_tokens` API, with byte-estimate fallback |
| TD-002 | **Narrowed** (Phase 1.5) | Gitea integration scaffolded, live PR creation behind hard fail pending git-push + workspace-rollback work |
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
- **PowerShell 5.1+ or PowerShell Core 7+** (for `Run-Validator.ps1` and `Promote-ToVerified.ps1`)
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

The golden corpus harness verifies parser and validator behavior against 50 fixtures across `approve` / `reject` / `escalate` / `adversarial` categories.

Run the parser stage (frontmatter parsing only, 59 assertions):

```bash
python pipeline/tests/run_harness.py --stage parser
```

Run the validator stage (full evaluation against deterministic stub responses, 225 assertions):

```bash
python pipeline/tests/run_harness.py --stage validator
```

Run all stages (deduplicated combined run, 244 assertions):

```bash
python pipeline/tests/run_harness.py --stage all
```

Expected output for `--stage all`: **`244 passed, 0 failed`** with **exit code 3**. Exit 3 is intentional — it signals that the integration stage is not yet implemented, not that any test has failed. The parser and validator stages both exit 0.

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

1. **Smoke-test the live Anthropic provider** against a real article and capture the result in the ledger.
2. **Wire the git-push + workspace-rollback path** in `Promote-ToVerified.ps1` to close the remaining TD-002 gap.
3. **Implement the integration test stage** so `--stage all` can exit 0.
4. **README and portfolio doc audit** to fully close TD-004.
5. Long-tail items tracked separately (no LICENSE/CI/dependency manifest historically — `requirements.txt` added at the public-push milestone).
