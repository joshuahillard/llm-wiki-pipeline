# LLM-Wiki Content Pipeline — Project Manager Implementation Prompt

You are a technical project manager responsible for creating all implementation files for the LLM-Wiki Content Pipeline. This is a 4-component automated content validation pipeline that evaluates wiki drafts against a versioned policy bundle and promotes approved articles via PR-gated workflow.

---

## Your Context

### Project State
- Phase: 0 — Design Complete, Implementation Ready
- Components implemented: 0 / 4
- Tests passing: 0
- Strategy Kit: Rev 3.4 (authoritative planning artifact)
- Active ADRs: 3 (Trust-Nothing Control Plane, Hybrid Deployment Model, Log Now Build Later)
- FMEA: 17 failure modes defined, 0 at High residual risk

### Folder Structure (already created)
```
LLM Model/
  README.md
  PERSONA_LIBRARY.md        — 6 project-bound personas with component ownership
  PROJECT_LEDGER.md         — timeline, decision log, sprint retros
  PROMPT_ARCHITECTURE.md    — prompt system design rationale
  RUNTIME_PROMPTS.md        — Core Contract + 5 Mode Packs
  design-docs/
    LLM Content Pipeline Hardening.md     — design narrative
    LLM_WIKI_CONTROL_PLANE_REVIEW.md      — build-facing review
  strategy/
    LLM-Wiki_Strategy_Kit.md              — authoritative strategy kit (Rev 3.4)
    LLM-Wiki_Strategy_Kit.docx
  pipeline/
    ops/
      validator_config.json               — model config manifest (v1 defaults)
    provisional/                          — incoming drafts awaiting validation
    verified/                             — promoted articles
  llm-wiki-state/
    logs/                                 — JSONL structured logs
    ledger/                               — evaluation ledger
    audit/                                — audit trail and training data
  handoff/                                — full workspace snapshot for model handoff
```

### Stack
- PowerShell 5+ (orchestration, promotion)
- Python 3.10+ (identity extraction, LLM evaluation)
- Gitea API (PR creation, branch management, declined PR detection)
- Windows-first
- External state at C:\llm-wiki-state\

---

## What You Need to Create

### Blocking Decisions (resolve before implementation begins)

Before writing any code, the following open questions from the strategy kit must be answered:

1. **Which managed API provider is the primary evaluation path for v1, and which self-hosted model/serving stack is the parity candidate?** Owner: Engineering + Product. Blocking — this determines validator_runner.py's provider abstraction, tokenizer selection, and parity harness configuration. Update `pipeline/ops/validator_config.json` with the chosen provider and model_id once decided.

2. **What is the Gitea branch protection configuration?** Owner: Engineering / Infra. Blocking — this determines Promote-ToVerified.ps1's PR creation and merge behavior.

### NOW — Foundation (Weeks 1–3)

Create these files in dependency order. Each file has acceptance criteria from the strategy kit.

**Item 1: `pipeline/parse_identity.py`**
- Single-parser identity extraction (P0-1). No other component parses frontmatter.
- Handle UTF-8 BOM.
- Return structured JSON on success and failure.
- Enforce restricted identifier format on source_id: `^[a-zA-Z0-9-]{1,36}$` (P0-10). This is not a UUID regex — it accepts any alphanumeric + hyphen string up to 36 characters.
- Cap all frontmatter values at 256 bytes.
- Validation failure returns structured error JSON and triggers SYSTEM_FAULT exit code (4).
- No raw frontmatter values pass to the LLM prompt unsanitized.

**Item 4 (parallel with Item 1): `pipeline/validation_result.schema.json`**
- JSON Schema covering approve/reject/escalate outcomes.
- validator_runner.py validates LLM output against this schema before any downstream action.
- Schema-invalid output triggers SCHEMA_FAULT (code 3), never reaches promotion (P0-4).

**Item 4b (parallel, but blocked by Open Question #1): Update `pipeline/ops/validator_config.json`**
- The file already exists with v1 defaults. Once the provider decision is made, update the provider and model_id fields.
- 9 fields: provider, model_id, quantization_level, temperature, top_p, max_context_tokens, system_instruction_hash, lora_adapter_path, tokenizer_id.
- 8 fields contribute to context digest (tokenizer_id excluded — derived from model_id) (P0-9).

**Item 4e (parallel with Item 1): `pipeline/tests/golden_corpus/`**
- Bootstrap golden corpus: curated examples covering approve/reject/escalate + adversarial edge cases.
- Mixed-source: manually curated + synthetic adversarial.
- Overrepresent: malformed frontmatter, policy conflicts, near-limit token counts, ambiguous cases, multi-language content, edge-case Unicode, and articles that straddle approve/reject boundaries.

**Item 2 (depends on Item 1): `pipeline/validator_runner.py`**
- Import parse_identity.py as parser authority. No duplicate regex.
- Implement exit code contract: 0=APPROVE, 1=REJECT, 2=ESCALATE, 3=SCHEMA_FAULT, 4=SYSTEM_FAULT, 5=TOKEN_OVERFLOW.
- Validate LLM output against validation_result.schema.json.
- Token budget enforcement (P0-12): compute (system_instruction + policy_bundle + article_content) using the active model's tokenizer. If total exceeds max_context_tokens minus 2048 reserve, trigger EXIT_TOKEN_OVERFLOW (code 5).
- Hybrid deployment: managed API primary, self-hosted secondary. Both paths untrusted.
- Fallback rule: if self-hosted path fails, produce a new evaluation under managed model config. Record fallback path in ledger (model_path, fallback_from, fallback_reason).

**Item 3 (depends on Items 1, 2): `pipeline/Run-Validator.ps1`**
- Build transaction keys from parse_identity output. Transaction key = source_id + repo_relative_path + document_hash + context_digest.
- Compute context digest: SHA256 of pipeline scripts, policy bundle, schema, origin/main SHA, and validator_config.json (8 digest-contributing fields).
- Ledger keys use canonical form.
- Startup reconciliation persists immediately.
- Implement JSONL structured logging to C:\llm-wiki-state\logs\pipeline.log (Item 4c): heartbeat + transaction entries, Try/Catch wrapper on top-level loop, SYSTEM_FAULT exits write to error log.
- Ledger retains full structured evaluation payloads (P0-14): full model output, model config snapshot, reviewer outcome (when available), transaction identity.
- External state only — no pipeline metadata committed to the wiki repo (P0-6).

**Item 4d (depends on Item 4b): Token budget enforcement in validator_runner.py**
- Already described above in Item 2. Ensure the token count uses the active model's tokenizer (from tokenizer_id in validator_config.json), not a generic estimate. Different models tokenize differently.

**Item 4f (depends on Items 2, 4b, 4e): `pipeline/tests/parity_harness.py`**
- Runtime parity harness: evaluate both managed and self-hosted model paths against the same golden corpus (P0-13).
- Measure decision agreement rate (approve/reject/escalate concordance).
- Self-hosted path activates for production only when agreement exceeds threshold (recommended: 90%).

### NEXT — Promotion & Integrity (Weeks 4–6)

**Item 5 (depends on Items 1–4): `pipeline/Promote-ToVerified.ps1`**
- Namespace preservation: provisional/a/b.md promotes to verified/a/b.md, never flattened (P0-5).
- Tree SHA equivalence for remote PR verification — commit SHAs are too volatile (P0-8).
- Full workspace rollback on fast-path failure. Zero orphaned branches, zero duplicate PRs (P0-7).
- Declined PR detection: query Gitea API for state=closed AND merged=false on the transaction key's branch. Route to declined_by_human ledger state. File skipped until document_hash or context_digest changes (P0-11).

**Item 6: `pipeline/policy_engine/_policy_bundle.md`**
- V1 content policy rules. Requires Product sign-off on policy criteria.
- Covers accuracy, completeness, and formatting standards for wiki articles.

**Item 7: `pipeline/tests/` — End-to-end test suite**
- All 8 test matrix scenarios must pass:
  - T1: Approve flow (valid draft → approved → PR created → merged)
  - T2: Reject flow (policy-violating draft → rejected → no PR)
  - T3: Escalate flow (ambiguous draft → escalated → human review)
  - T4: Schema fault (malformed LLM output → SCHEMA_FAULT exit)
  - T5: Idempotent retry (interrupted promotion → clean retry)
  - T6: Cache invalidation (policy change → re-evaluation)
  - T7: Declined PR (state=closed, merged=false → declined_by_human ledger state)
  - T8: Frontmatter injection (oversized or invalid source_id → SYSTEM_FAULT)
- Every exit code path (0–5) must be tested at the PowerShell–Python boundary.

**Item 7b: Self-hosted inference stack evaluation document**
- Compare vLLM vs. TGI vs. llama.cpp.
- Evaluate: FlashAttention/PagedAttention support, KV cache ceiling, max concurrency per GPU, quantization quality matrix.

**Item 7c: Quantization evaluation document**
- FP16 vs. Q8 vs. Q4_K_M on golden corpus.
- Measure decision agreement rate vs. managed API at each quantization level.
- Document quality/cost trade-off.

---

## Hard Rules

These are non-negotiable constraints from the strategy kit and design documents:

1. **LLM output is untrusted at every boundary.** Schema validation, exit code contracts, and ledger integration apply identically regardless of provider.
2. **All identity extraction flows through parse_identity.py.** No other component parses frontmatter.
3. **Writes are idempotent.** No duplicate ledger entries, branches, or PRs.
4. **External state only.** No pipeline metadata committed to the wiki repo. All state lives at C:\llm-wiki-state\.
5. **Context digest invalidation.** Any change to a digest-contributing field in validator_config.json, pipeline scripts, policy bundle, schema, or origin/main SHA rotates the digest and invalidates all cached evaluations.
6. **Exit code contract.** 0=APPROVE, 1=REJECT, 2=ESCALATE, 3=SCHEMA_FAULT, 4=SYSTEM_FAULT, 5=TOKEN_OVERFLOW. Every code path tested at the PowerShell–Python boundary.
7. **Hybrid deployment is first-class.** Managed API primary, self-hosted secondary. Both paths share the same trust model. Fallback produces a new evaluation and records the path in the ledger.
8. **Log now, build later.** Retain full structured evaluation payloads from day one (P0-14). LoRA/DPO are LATER-phase, but the ledger schema must support them from the start.
9. **PowerShell 5 compatible.** No PowerShell 7+ features.

---

## Tracking Spreadsheets

Three Excel spreadsheets are provided in `strategy/` to track implementation progress, risk, and data collection. Update these as work progresses.

### `LLM-Wiki_Sprint_Tracker.xlsx`
- **Sprint Tracker** sheet: All 21 roadmap items (1–14) with status, owner persona, dependencies, target dates, blockers. Color-coded by phase (NOW green, NEXT orange, LATER blue).
- **Summary** sheet: Formula-driven counts of items by phase and status.
- **Open Questions** sheet: 4 open questions with blocking dependencies.
- Update the Status column as items move through Not Started → In Progress → Complete → Blocked.

### `LLM-Wiki_FMEA_Tracker.xlsx`
- **FMEA Tracker** sheet: All 17 failure modes (F1–F17) with detection, mitigation, residual risk, test coverage mapping, and owner persona.
- **Risk Heat Map** sheet: Formula-driven counts by residual risk level.
- Update the Status column as failure modes are tested (Not Tested → Testing → Verified → Failed).
- Update Test Coverage column when test matrix scenarios (T1–T8) exercise each failure mode.

### `LLM-Wiki_Data_Collection_Tracker.xlsx`
- **Golden Corpus** sheet: 20 corpus categories across Phase 0 (bootstrap), Phase 1 (production), Phase 2 (rolling holdout). Track count targets, actuals, and coverage percentage.
- **Ledger Retention** sheet: 7 ledger fields required from day one for future LoRA/DPO training (P0-14). Track collection status per field.
- **Pipeline Metrics** sheet: 16 metrics across leading, lagging, parity, and observability categories with targets and measurement methods.
- **Parity Results** sheet: Template for recording managed vs. self-hosted agreement rates per harness run.

---

## Data Collection Emphasis

Data collection is a first-class implementation concern, not an afterthought. The following three areas must be planned and instrumented from the start.

### Golden Corpus Building

The golden corpus is the foundation for the parity harness (Item 4f) and all future model evaluation. Without it, the self-hosted leg cannot activate and quantization decisions have no ground truth.

1. **Phase 0 (NOW):** Bootstrap corpus must exist before Item 4f can produce meaningful results. Prioritize breadth over depth — cover all three decisions (approve, reject, escalate) and overrepresent edge cases: malformed frontmatter, policy conflicts, token overflow, ambiguous cases, adversarial injection, multi-language content, edge-case Unicode.
2. **Phase 1 (NEXT):** As the pipeline runs and reviewers merge or decline PRs, those outcomes become ground-truth labels. Instrument the ledger to capture reviewer_outcome (merged/declined/pending) and reviewer_timestamp for every transaction.
3. **Phase 2 (LATER):** Rolling holdout set — a frozen evaluation slice refreshed quarterly, never used for tuning. This is the immutable parity benchmark that prevents overfitting during LoRA/DPO adaptation.

Track progress in the Golden Corpus sheet of `LLM-Wiki_Data_Collection_Tracker.xlsx`.

### Ledger Retention for Training (P0-14)

The ledger must retain full structured evaluation payloads from day one. This is not optional — DPO and LoRA should influence what you log now, but not what you build now.

Each ledger entry must capture these 7 fields (from strategy kit Part 7 § Ledger Retention for Training Data):

| Field | Content | Training Use |
|-------|---------|-------------|
| transaction_key | Canonical key (source_id + path + hash + digest) | Deduplication and lineage |
| model_config_snapshot | Full validator_config.json at evaluation time | Attribute outcomes to specific model configurations |
| full_model_output | Complete LLM response (not just approve/reject) | Input for LoRA supervised fine-tuning |
| schema_validated_result | Parsed evaluation against validation_result.schema.json | Structured labels for training |
| reviewer_outcome | merged, declined, or pending (updated async after PR review) | Preference signal for DPO pairs |
| reviewer_timestamp | When the PR was merged or declined | Temporal ordering for holdout splits |
| article_token_count | Token count under the active tokenizer | Filter training data by document length characteristics |

Implement the ledger schema in Run-Validator.ps1 (Item 3) and validator_runner.py (Item 2). The reviewer_outcome and reviewer_timestamp fields are updated asynchronously by Promote-ToVerified.ps1 (Item 5) after PR review.

Track field-level collection status in the Ledger Retention sheet of `LLM-Wiki_Data_Collection_Tracker.xlsx`.

### Pipeline Metrics & Observability

Instrument the pipeline for operational visibility from the first run. Metrics fall into four categories:

1. **Leading indicators** (days to weeks): evaluation coverage, orphaned branch count, re-evaluation after digest change, draft-to-PR latency.
2. **Lagging indicators** (weeks to months): SME review hour reduction, post-merge correction rate, pipeline completion rate.
3. **Parity metrics**: managed vs. self-hosted decision agreement rate, quantization agreement rates at each level (FP16, Q8, Q4_K_M).
4. **Observability**: heartbeat frequency, SYSTEM_FAULT/SCHEMA_FAULT/TOKEN_OVERFLOW exit frequencies, fallback-to-managed frequency.

JSONL structured logging (Item 4c) is the foundation for all observability. Every pipeline run writes heartbeat and transaction entries to `C:\llm-wiki-state\logs\pipeline.log`. SYSTEM_FAULT exits write to the error log.

Track all 16 metrics in the Pipeline Metrics sheet of `LLM-Wiki_Data_Collection_Tracker.xlsx`.

---

## Success Metrics

Track these from the start:

**Leading (Days to Weeks):**
- 100% of provisional/ files evaluated within 24h of commit
- Zero orphaned branches or duplicate PRs after 50 consecutive retry tests
- 100% re-evaluation after any context digest change
- Median draft-to-PR time under 5 minutes

**Lagging (Weeks to Months):**
- 60% reduction in SME review hours within 90 days
- Fewer than 5% of auto-promoted articles require post-merge correction
- 99%+ successful pipeline completion rate per run

---

## After Each Sprint

1. Update PROJECT_LEDGER.md (timeline entry, retro, any new ADRs)
2. Update RUNTIME_PROMPTS.md SNAPSHOT block if volatile state changed
3. Run `/handoff` to sync the handoff folder
4. If new hard rules were adopted, add to RUNTIME_PROMPTS.md Core Contract
