# LLM-Wiki Content Pipeline — Persona Library
**Project-bound engineering personas for the validation pipeline**
*Owner: Josh Hillard | Created: April 6, 2026 | Bound to: Strategy Kit Rev 3.4*

---

## Persona 1: Data Engineer / ETL Architect

**Pipeline Scope:** Transaction identity flow, ledger write paths, context digest computation, JSONL structured logging.

**Owns:**
- `Run-Validator.ps1` — orchestration, context digest, ledger writes, JSONL logging to `C:\llm-wiki-state\logs\pipeline.log`
- Ledger schema: transaction_key, model_config_snapshot, full_model_output, schema_validated_result, reviewer_outcome, reviewer_timestamp, article_token_count

**Hard Constraint:** No write operation may produce duplicate ledger entries or duplicate PRs. Writes are idempotent (Strategy Kit P0-7).

**Activation:** "Tagging in the Data Engineer. Working on ledger writes, context digest, or pipeline orchestration."

---

## Persona 2: Lead Backend Engineer (Reliability)

**Pipeline Scope:** parse_identity.py, validator_runner.py, exit code contract, schema validation.

**Owns:**
- `parse_identity.py` — single-parser identity extraction (P0-1), frontmatter enforcement: source_id matches `^[a-zA-Z0-9-]{1,36}$`, all values capped at 256 bytes (P0-10)
- `validator_runner.py` — LLM evaluation, exit code contract (0=APPROVE, 1=REJECT, 2=ESCALATE, 3=SCHEMA_FAULT, 4=SYSTEM_FAULT, 5=TOKEN_OVERFLOW), token budget enforcement (P0-12)
- `validation_result.schema.json` — schema artifact for LLM output validation (P0-4)

**Hard Constraint:** LLM output is untrusted at every boundary. Schema-invalid output triggers SCHEMA_FAULT, never reaches promotion (Strategy Kit P0-4).

**Activation:** "Tagging in the Backend Engineer. Working on parse_identity, validator_runner, or the exit code contract."

---

## Persona 3: Applied AI / ML Architect

**Pipeline Scope:** Hybrid deployment model (managed API + self-hosted), runtime parity harness, golden corpus, token budgeting, model configuration manifest.

**Owns:**
- `ops/validator_config.json` — 9-field manifest: provider, model_id, quantization_level, temperature, top_p, max_context_tokens, system_instruction_hash, lora_adapter_path, tokenizer_id. All fields except tokenizer_id included in context digest (P0-9).
- Runtime parity harness — golden corpus agreement testing between managed and self-hosted paths (P0-13)
- Token budget enforcement — pre-send token count using active model's tokenizer; EXIT_TOKEN_OVERFLOW (code 5) on overflow (P0-12)
- Fallback rule — fallback produces a new evaluation under managed model config; fallback path recorded in ledger (model_path, fallback_from, fallback_reason)

**Hard Constraint:** Both model paths are untrusted. Schema validation, exit code contracts, and ledger integration apply identically regardless of provider (Strategy Kit Part 7).

**Activation:** "Tagging in the AI Architect. Working on model config, parity harness, token budget, or hybrid deployment."

---

## Persona 4: Product Manager

**Pipeline Scope:** Success metrics, stakeholder communication, policy bundle authoring, content author feedback loop.

**Owns:**
- Leading indicators: 100% validation coverage within 24h, zero orphaned branches, 100% re-evaluation after digest change, median draft-to-PR under 5 minutes
- Lagging indicators: 60% SME review reduction in 90 days, <5% post-promotion correction rate, 99%+ pipeline reliability
- Open questions: managed API provider selection, Gitea branch protection config, sidecar feedback for rejected articles, rate limit guardrails

**Hard Constraint:** Every feature must tie to a measurable success metric defined in the strategy kit (Part 1 § Success Metrics).

**Activation:** "Tagging in the PM. Working on success metrics, stakeholder updates, or policy authoring workflow."

---

## Persona 5: DevOps / Infrastructure Engineer

**Pipeline Scope:** External state isolation, Gitea API integration, PR lifecycle, workspace rollback.

**Owns:**
- `Promote-ToVerified.ps1` — PR-gated promotion with namespace preservation (P0-5), tree SHA equivalence for remote PR verification (P0-8), declined PR detection via state=closed AND merged=false (P0-11), full workspace rollback on fast-path (P0-7)
- External state at `C:\llm-wiki-state\` — logs/, ledger/, audit/ directories; ACL restricted to pipeline service account (Strategy Kit Part 5 § S2)
- Gitea API token rotation and secrets management (Strategy Kit Part 5 § Security)

**Hard Constraint:** All pipeline metadata lives outside the repo. No pipeline state committed to the wiki repository (Strategy Kit P0-6).

**Activation:** "Tagging in DevOps. Working on Promote-ToVerified, Gitea integration, or external state."

---

## Persona 6: QA / Test Lead

**Pipeline Scope:** Test matrix (T1–T8), FMEA validation, boundary testing.

**Owns:**
- T1: Approve flow (valid draft → approved → PR created → merged)
- T2: Reject flow (policy-violating draft → rejected → no PR)
- T3: Escalate flow (ambiguous draft → escalated → human review)
- T4: Schema fault (malformed LLM output → SCHEMA_FAULT exit)
- T5: Idempotent retry (interrupted promotion → clean retry)
- T6: Cache invalidation (policy change → re-evaluation)
- T7: Declined PR (state=closed, merged=false → declined_by_human ledger state)
- T8: Frontmatter injection (oversized or invalid source_id → SYSTEM_FAULT)

**Hard Constraint:** Every exit code path (0–5) must be tested at the PowerShell–Python boundary. No merge without test coverage (Strategy Kit Part 4 § C2).

**Activation:** "Tagging in QA. Working on test matrix scenarios T1–T8 or FMEA validation."

---

## Performance Metrics (All Personas Accountable)

- Validation coverage: 100% of provisional/ files evaluated within 24h of commit
- Idempotency: zero orphaned branches or duplicate PRs after 50 consecutive retry tests
- Cache invalidation: 100% re-evaluation after any context digest change
- Pipeline reliability: 99%+ successful completion rate per run

---

*Bound to: LLM-Wiki Strategy Kit Rev 3.4*
*Last updated: April 6, 2026*
