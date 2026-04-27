# LLM-Wiki Content Pipeline — Runtime Prompts
**Copy-paste blocks for AI sessions. Everything here is model input.**
*Version: 1.0 | April 6, 2026 | Bound to: Strategy Kit Rev 3.4*

---

## CORE CONTRACT

Paste once at session start.

```
LLM-WIKI CORE v1.0

Project: Automated content validation pipeline for wiki repositories.
  LLM evaluates drafts in provisional/ against a versioned policy bundle,
  promotes approved articles to verified/ via PR-gated workflow.

Core flow: provisional/ → parse_identity.py → validator_runner.py → Run-Validator.ps1 → Promote-ToVerified.ps1 → verified/

Stack: PowerShell 5+, Python 3.10+, Gitea API, Windows-first, external state at C:\llm-wiki-state\

Exit codes: 0=APPROVE, 1=REJECT, 2=ESCALATE, 3=SCHEMA_FAULT, 4=SYSTEM_FAULT, 5=TOKEN_OVERFLOW

Rules:
- Read each file before editing it. Search before assuming symbols exist.
- LLM output is untrusted at every boundary. Validate against validation_result.schema.json before use.
- All identity extraction flows through parse_identity.py. No other component parses frontmatter.
- Writes are idempotent. No duplicate ledger entries, branches, or PRs.
- External state only: no pipeline metadata committed to the wiki repo.
- Context digest includes: pipeline scripts, policy bundle, schema, origin/main SHA, validator_config.json (8 of 9 fields; tokenizer_id excluded).
- PowerShell 5 compatible. No PowerShell 7+ features.
- Run targeted verification and report what actually passed.

Key paths:
- Identity:    pipeline/parse_identity.py
- Evaluation:  pipeline/validator_runner.py
- Orchestration: pipeline/Run-Validator.ps1
- Promotion:   pipeline/Promote-ToVerified.ps1
- Model config: pipeline/ops/validator_config.json
- Schema:      pipeline/validation_result.schema.json
- Logs:        C:\llm-wiki-state\logs\pipeline.log (JSONL)
- Ledger:      C:\llm-wiki-state\ledger\
- Drafts:      pipeline/provisional/
- Published:   pipeline/verified/
- Design docs: design-docs/
- Strategy:    strategy/LLM-Wiki_Strategy_Kit.md
```

---

## TASK CARD TEMPLATE

One per unit of work. Fill in and paste after Core Contract.

```
TASK: [short title]

Goal: [what and why, 1-2 sentences]
Scope: [what's in bounds]
Out of scope: [what to leave alone]

Inspect first:
- [path::symbol references]

Acceptance:
- [testable outcome from strategy kit requirements]

Verify:
- [targeted test or check command]

Deliver:
- implement changes
- summarize touched files
- report verification honestly
```

---

## MODE PACKS

Append after Task Card when the task enters a specific domain.

### MODE: identity
```
MODE: identity
- All frontmatter parsing goes through parse_identity.py. No exceptions.
- source_id must match ^[a-zA-Z0-9-]{1,36}$ (restricted identifier format, not UUID).
- All frontmatter values capped at 256 bytes.
- Validation failure returns structured error JSON and triggers SYSTEM_FAULT (code 4).
- No raw frontmatter values pass to the LLM prompt unsanitized.
- UTF-8 BOM handling required.
```

### MODE: evaluation
```
MODE: evaluation
- validator_runner.py imports parse_identity. No duplicate regex.
- Exit codes: 0=APPROVE, 1=REJECT, 2=ESCALATE, 3=SCHEMA_FAULT, 4=SYSTEM_FAULT, 5=TOKEN_OVERFLOW.
- LLM output validated against validation_result.schema.json before any downstream action.
- Token budget: compute (system_instruction + policy_bundle + article_content) using active model's tokenizer.
  Overflow (exceeds max_context_tokens - 2048 reserve) triggers EXIT_TOKEN_OVERFLOW.
- Schema-invalid output triggers SCHEMA_FAULT. Never reaches promotion.
- Hybrid deployment: managed API primary, self-hosted secondary. Both paths untrusted.
- Fallback: produces new evaluation under managed config; path recorded in ledger.
```

### MODE: promotion
```
MODE: promotion
- Promote-ToVerified.ps1 preserves namespace: provisional/a/b.md → verified/a/b.md.
- Tree SHA equivalence for remote PR verification (commit SHAs too volatile).
- Full workspace rollback on fast-path failure. Zero orphaned state.
- Declined PR detection: state=closed AND merged=false via Gitea API.
- Declined files route to declined_by_human ledger state; skipped until doc_hash or context_digest changes.
- No pipeline metadata committed to wiki repo.
```

### MODE: config
```
MODE: config
- ops/validator_config.json is the System Configuration Manifest.
- 9 fields: provider, model_id, quantization_level, temperature, top_p, max_context_tokens,
  system_instruction_hash, lora_adapter_path, tokenizer_id.
- 8 fields contribute to context digest (tokenizer_id excluded — derived from model_id).
- Any digest-contributing field change invalidates all cached evaluations.
- JSONL logging to C:\llm-wiki-state\logs\pipeline.log (heartbeat + transaction entries).
```

### MODE: product
```
MODE: product
- Owner: Josh Hillard — cross-functional audience (engineering + product).
- Value mapping: every feature ties to success metrics in Strategy Kit Part 1.
- Leading: 100% validation coverage (24h), zero orphaned branches, 100% re-eval after digest change, <5min draft-to-PR.
- Lagging: 60% SME reduction (90d), <5% post-promotion correction, 99%+ reliability.
- Update PROJECT_LEDGER.md after shipping.
```

---

## SNAPSHOT (optional)

Attach only when the task depends on volatile repo state.

```
SNAPSHOT:
- Branch: [branch] | Tag: [tag]
- Tests: [count] passing
- Known issues: [relevant blockers]
- Recent context: [1-2 sentences]
```

---

## CONTINUATION (for multi-message tasks)

```
Continue from commit [hash].
[Part/step] done. Now: [next objective].
State: [1-2 sentences of what changed].
```

---

*See PROMPT_ARCHITECTURE.md for design rationale.*
*Bound to: LLM-Wiki Strategy Kit Rev 3.4*
