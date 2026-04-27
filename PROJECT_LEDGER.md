# LLM-Wiki Content Pipeline — Project Ledger
**Canonical Timeline, Decision Log & Sprint Retrospectives**
*Owner: Josh Hillard | Created: April 6, 2026 | Living document — update after every sprint*

---

## Project Timeline

### Phase 0 — Design Complete (April 6, 2026)

**What happened:** Designed a 4-component control plane (Run-Validator.ps1, parse_identity.py, validator_runner.py, Promote-ToVerified.ps1) for automated wiki content validation. Produced two design narratives (LLM Content Pipeline Hardening, LLM_WIKI_CONTROL_PLANE_REVIEW) and a comprehensive strategy kit (Rev 3.4) covering PRD, ADR, roadmap, code review, stakeholder perspectives, FMEA (17 failure modes), and LLM infrastructure plan. Established hybrid deployment model (managed API + self-hosted) as a first-class architectural posture. Created folder infrastructure for pipeline runtime, external state, and workspace organization.

**Artifacts:**
- strategy/LLM-Wiki_Strategy_Kit.md (Rev 3.4)
- strategy/LLM-Wiki_Strategy_Kit.docx (Rev 3.4)
- design-docs/LLM Content Pipeline Hardening.md
- design-docs/LLM_WIKI_CONTROL_PLANE_REVIEW.md
- pipeline/ops/validator_config.json (v1 defaults)
- PERSONA_LIBRARY.md (6 personas, project-bound)
- RUNTIME_PROMPTS.md (Core Contract + 5 Mode Packs)
- PROMPT_ARCHITECTURE.md

**Test count:** 0
**Status:** Implementation Ready — roadmap Item 1 (parse_identity.py) is the first deliverable.

### Phase 1 — Parser & Test Harness (April 6, 2026)

**What happened:** Implemented parse_identity.py (Roadmap Item 1) — frontmatter parser and transaction identity generator. Built golden corpus with 26 fixtures across 5 buckets (4 approve, 4 reject, 3 escalate, 14 adversarial, 1 integration). Created deterministic test harness (run_harness.py, validator_runner.py, schema_helpers.py, validate_schema.py) and validation_result.schema.json for output envelopes. Established VIOLATION_TAXONOMY.md with 11 concrete rule IDs. Created PM_IMPLEMENTATION_PROMPT.md and 3 Excel trackers (Sprint, FMEA, Data Collection).

**Artifacts:**
- pipeline/parse_identity.py (Phase 1 deliverable)
- pipeline/validation_result.schema.json
- pipeline/tests/run_harness.py, validator_runner.py, schema_helpers.py, validate_schema.py
- pipeline/tests/golden_corpus/ (26 fixtures + manifest + schema + priority guide)
- pipeline/policy_engine/VIOLATION_TAXONOMY.md (11 rule IDs)
- strategy/PM_IMPLEMENTATION_PROMPT.md
- strategy/LLM-Wiki_Sprint_Tracker.xlsx, LLM-Wiki_FMEA_Tracker.xlsx, LLM-Wiki_Data_Collection_Tracker.xlsx

**Test count:** 23/23 golden corpus files validated (13 adversarial produce expected errors, 10 parse successfully)
**Status:** Roadmap Item 2 next — update validator_runner.py to use parse_identity.py as parser authority.

### Phase 0.5 — Production-Readiness Specifications (April 6, 2026)

**What happened:** Gap analysis identified four missing specification layers (telemetry, governance, author feedback, corpus maintenance) and two operational artifacts (coverage map, definition of done) needed to elevate the project from a technical foundation to a production-grade portfolio piece. Created all six artifacts, each grounded in existing schemas and real corpus data. Cross-reference audit verified consistency across all artifacts and against source files (validation_result.schema.json, VIOLATION_TAXONOMY.md, CORPUS_MANIFEST.md, validator_config.json).

**Artifacts:**
- strategy/TELEMETRY_SPEC.md — JSONL event schema (9 event types), 4 SLI definitions with calculation logic, exit code → fault category mapping with FMEA cross-references (F1-F17)
- strategy/GOVERNANCE_FRAMEWORK.md — one-page editorial philosophy, severity-to-decision rationale chain for all 4 severity levels, human-in-the-loop boundary definition
- strategy/FEEDBACK_SPEC.md — projection logic from validation_result.schema.json, line-level referencing contract (section/line/frontmatter), .feedback.md sidecar format, remediation loop
- strategy/CORPUS_MAINTENANCE_SOP.md — T7/T8 corrected pair trigger, sanitize-classify-tag action sequence with provenance metadata, 30% adversarial ratio constraint, baseline snapshot protocol
- strategy/GOLDEN_CORPUS_COVERAGE_MAP.md — 5-category policy violation heat map, 7 prioritized testing deserts (NEUTRALITY-001, FORMATTING-002, SECURITY-003, COMPLETENESS-004 at zero coverage), growth targets maintaining adversarial floor
- strategy/DEFINITION_OF_DONE.md — 7 quality gates (Logic, Security, Identity, Telemetry, Contract, Audit, Documentation) with evidence requirements, gate applicability matrix for all NOW-phase roadmap items

**Key findings:**
- 4 testing deserts identified: NEUTRALITY-001, FORMATTING-002, SECURITY-003, COMPLETENESS-004 have zero dedicated fixture coverage
- Accuracy rejection coverage is thinner than assumed (2 fixtures, not 3 — E-001 is an escalation case)
- ADV-014 primarily tests token overflow, not formatting policy — formatting coverage is effectively zero

**Test count:** 23/23 (unchanged — no implementation work this phase)
**Status:** Specification layer complete. Roadmap Item 2 next — update validator_runner.py to use parse_identity.py as parser authority.

### Phase 0.6 — Desert Closure, Runtime Bootstrap & Portfolio Hardening (April 6, 2026)

**What happened:** Closed the four Priority 1-4 testing deserts identified in the coverage map by expanding the golden corpus from 26 to 30 fixtures and adding deterministic canned validator responses so the validator-stage harness could run end-to-end. Added dedicated coverage for NEUTRALITY-001, FORMATTING-002, SECURITY-003, and COMPLETENESS-004 while keeping fixture decisions aligned to the current governance framework rather than inventing a harsher policy contract. Created the previously-missing runtime artifacts (`Run-Validator.ps1`, `Promote-ToVerified.ps1`, `SYSTEM_PROMPT.md`, `_policy_bundle.md`) as bootstrap implementations and updated `validator_config.json` to bind the new system prompt into the runtime manifest. In parallel, drafted and hardened a portfolio-facing documentation spine (trust model, trust boundaries, identity/auditability, schema contract, corpus design, governance, and PM discipline) so the wiki reflects the same control-plane rules as the strategy kit.

**Artifacts:**
- pipeline/tests/golden_corpus/approve/A-005-vendor-specific-guidance.md — closes the neutrality desert with an approve-path observation fixture
- pipeline/tests/golden_corpus/approve/A-006-broken-markdown.md — closes the broken-markdown desert
- pipeline/tests/golden_corpus/approve/A-007-missing-critical-section.md — closes the missing-critical-section desert
- pipeline/tests/golden_corpus/reject/R-005-contains-pii.md — closes the PII desert
- pipeline/tests/golden_corpus/responses/ (21 deterministic canned responses) — enables validator-stage harness execution without live provider dependency
- pipeline/tests/golden_corpus/corpus_manifest.json, CORPUS_MANIFEST.md — updated to fixture_version 1.1 and 30-fixture corpus state
- strategy/GOLDEN_CORPUS_COVERAGE_MAP.md — updated to reflect desert closure and new remaining priorities
- pipeline/Run-Validator.ps1 — bootstrap orchestration: context digest, parser/validator invocation, JSONL logging, ledger writes, feedback sidecars
- pipeline/Promote-ToVerified.ps1 — bootstrap promotion preflight: namespace-preserving destination, branch alias derivation, audit preview, fail-closed until Gitea wiring exists
- pipeline/SYSTEM_PROMPT.md — runtime validator instruction contract
- pipeline/policy_engine/_policy_bundle.md — runtime-facing policy bundle v1 aligned to taxonomy and governance
- pipeline/ops/validator_config.json — updated with system_instruction_hash from SYSTEM_PROMPT.md
- Foundations/LLM System Trust Model.md
- Foundations/Trust Boundaries in LLM Pipelines.md
- Foundations/Transaction Identity and Auditability.md
- Foundations/Schema Validation for LLM Output.md
- Foundations/Golden Corpus Design.md
- Governance/Human-in-the-Loop Governance.md
- Program-Management/Program Management for Technical Infrastructure.md

**Key findings:**
- The validator harness was blocked not by model logic, but by the absence of the `golden_corpus/responses/` directory. Adding deterministic responses converted the validator stage from a partial harness to a real executable gate.
- The P1-P4 testing deserts are now closed at the corpus layer. `FORMATTING-001`, plus deeper non-escalation coverage for ACCURACY-003 and ACCURACY-004, remain the next calibration targets.
- Runtime artifact presence is no longer a portfolio gap, but the runtime remains bootstrap-grade: `Run-Validator.ps1` currently drives the validator under `pipeline/tests/`, and `Promote-ToVerified.ps1` is intentionally fail-closed until Gitea-backed PR behavior is wired.
- The portfolio documentation is now much more contract-shaped, but the remaining implementation gaps are clearer rather than smaller: production `pipeline/validator_runner.py`, live PR promotion, and canonical repo-root-relative identity remain the next engineering steps.

**Test count:** 166/166 assertions passing — parser harness 37/37, validator harness 129/129. Additional smoke checks passed for `Run-Validator.ps1 -DryRun` (empty queue + single-file evaluation) and `Promote-ToVerified.ps1 -DryRun` (namespace-preserving promotion preview).
**Status:** Desert closure complete. Bootstrap runtime artifacts now exist. Next step remains unchanged at the control-plane level: promote the validator from `pipeline/tests/validator_runner.py` into a production `pipeline/validator_runner.py`, then complete live Gitea-backed promotion behavior.

### Phase 0.7 — Continuation Review & Academic Source Intake (April 7, 2026)

**What happened:** Performed a dated continuity review to confirm where the project actually stopped on April 6, 2026. Verified that the repository state still matches the recorded handoff: the bootstrap runtime exists, `Run-Validator.ps1` still targets `pipeline/tests/validator_runner.py`, and the next engineering step remains promotion of the validator into a production `pipeline/validator_runner.py`. Added an academic-only source map for LLMs, coding/software engineering, agent evaluation, retrieval, and governance using only university-hosted sources from Stanford, Princeton, UC Berkeley, MIT, and Carnegie Mellon. Updated the README to reflect the real workspace structure and reduce current documentation drift.

**Artifacts:**
- LLM/Academic Source Map - LLM, Coding, and Governance.md
- README.md
- PROJECT_LEDGER.md

**Key findings:**
- The continuation point is unchanged from April 6, 2026. No hidden implementation branch was found in the workspace.
- The most credible academic inputs for the next phase cluster around five themes: foundation-model framing, holistic evaluation, repository-scale software engineering benchmarks, execution-aware code evaluation, and agent-evaluation rigor.
- README drift was real: the prior structure referenced `templates/`, which is not present in the workspace. The README now matches the actual folder layout more closely.

**Test count:** 166/166 remains the latest recorded passing implementation baseline. No new runtime code was added in this phase.
**Status:** Continuity re-established for April 7, 2026. The next engineering step is still production `pipeline/validator_runner.py`, with the new academic source map available to guide design and evaluation choices.

### Phase 0.8 — Production Validator Promotion (April 7, 2026)

**What happened:** Promoted the validator from the test-only location into a production runtime module at `pipeline/validator_runner.py` and created a production `pipeline/schema_helpers.py` so runtime imports no longer depend on `pipeline/tests/`. Preserved the existing harness contract by converting the test-side `schema_helpers.py` and `validator_runner.py` files into thin wrappers over the production modules, and updated `pipeline/tests/run_harness.py` to load the production validator path directly. Updated `Run-Validator.ps1` to invoke the production validator and tightened a real control-plane integrity gap: the effective validator config used at runtime is now also the config reflected in the context digest and ledger snapshot, rather than hashing one provider path while executing another.

**Artifacts:**
- pipeline/validator_runner.py
- pipeline/schema_helpers.py
- pipeline/tests/validator_runner.py
- pipeline/tests/schema_helpers.py
- pipeline/tests/run_harness.py
- pipeline/Run-Validator.ps1
- README.md
- PROJECT_LEDGER.md

**Key findings:**
- The validator promotion is behavior-preserving at the harness layer: parser assertions remained 37/37 and validator assertions remained 129/129 after the move.
- `Run-Validator.ps1 -DryRun` now executes successfully through the production validator path for both an empty queue and a temporary real article staged into `pipeline/provisional/`.
- A direct CLI invocation of `pipeline/validator_runner.py` with the checked-in `validator_config.json` still fails on `vertex_ai`, which is expected because provider integration is still pending. The orchestration layer therefore continues to force the deterministic `stub` provider to preserve bootstrap behavior.
- The production validator is now a real runtime artifact, but live provider wiring is still an open engineering step rather than hidden drift.

**Test count:** 166/166 baseline preserved — parser harness 37/37, validator harness 129/129. Additional smoke checks passed for `Run-Validator.ps1 -DryRun` on both empty-queue and single-file paths through the production validator.
**Status:** Production validator promotion complete and verified. The next engineering steps are live provider integration in `pipeline/validator_runner.py`, live promotion behavior in `Promote-ToVerified.ps1`, and canonical repo-root-relative identity in `parse_identity.py`.

### Phase 0.9 — Research Intake Review (April 7, 2026)

**What happened:** Reviewed an external local draft (not included in this repository) against the current repository state. Confirmed that the draft is directionally aligned with the project's trust/governance posture, but not yet synced to repo reality: the repository does not currently contain a verified 600-source academic bibliography or a 100-item adversarial corpus. Added an intake-review note to preserve the research direction without promoting unverified or mixed-provenance claims into the canonical source-of-truth docs.

**Artifacts:**
- LLM/Pillars of Truth - Intake Review.md

**Key findings:**
- The repo currently contains a curated academic source map, not a 600-source verified bibliography.
- The executable corpus currently contains 30 fixtures total, including 14 adversarial fixtures, not 100 adversarial fixtures.
- Quick verification confirmed several strong anchors (for example Stanford FMTI/HELM, Princeton SWE-bench, Berkeley LiveCodeBench, MIT ID-RAG), but the external draft also mixes in non-academic or mixed-provenance entries such as OWASP, OpenTelemetry, Anthropic, Redis, and news-style pages.
- The research direction is valuable, but the source list should be split into verified academic anchors versus draft/mixed references before it is elevated into canonical project doctrine.

**Test count:** 166/166 remains the latest verified implementation baseline. No runtime behavior changed in this phase.
**Status:** Research intake captured, but not yet canonized. Recommended next documentation step is a machine-readable verified bibliography plus an F1-F17 adversarial fixture expansion plan.

### Phase 0.10 — Machine-Readable Bibliography Expansion (April 7, 2026)

**What happened:** Built out a machine-readable academic bibliography in a private research vault (not included in this repository). Expanded the bibliography in reviewed batches from a small seed set into a canonical `77`-source verified collection with one Markdown note per source, a schema, a JSON export, and a CSV export. Preserved the academic-only sourcing rule by limiting additions to official academic or academic-center hosts and recording source metadata, verification dates, and note paths for every entry. Added coverage across all six pillars and materially expanded institutional breadth to include Harvard, Penn, Columbia, Brown, Dartmouth, Johns Hopkins, Cornell, Yale, and others alongside the existing Stanford, Princeton, Berkeley, MIT, and CMU foundation.

**Artifacts:**
- Machine-readable bibliography (77 sources, JSON + CSV + per-source notes) maintained in a private research vault — not included in this repository
- PROJECT_LEDGER.md

**Key findings:**
- The verified bibliography now contains `77` academic sources with `0` duplicate IDs and `0` broken note paths.
- Coverage at end of day is: `evaluation` 18, `software_engineering` 17, `governance` 10, `rag_provenance` 10, `observability` 11, `hardening` 11.
- Harvard and University of Pennsylvania are now clearly present in the canonical set across multiple pillars rather than being isolated to one area. Harvard stands at 6 entries and Penn at 5.
- The research layer now works cleanly with plain Obsidian browsing and remains compatible with Obsidian Bases because the source notes use consistent frontmatter and do not depend on Dataview.
- The main remaining research weakness is distribution across institutions inside `observability` and `software_engineering`: Dartmouth and Northwestern still have no representation in those two pillars, and several other schools remain thin in observability.

**Test count:** No runtime code changed in this phase. The latest verified implementation baseline remains 166/166. Bibliography integrity verification passed at `77` JSON entries, `77` CSV rows, and `77` source-note files.
**Status:** Machine-readable bibliography layer established and significantly expanded. The next research step is targeted pillar balancing, especially observability coverage for thinner institutions, plus optional Obsidian pillar index notes for easier navigation.

### Phase 1.0 — Deterministic Repo-Root Identity (April 8, 2026)

**What happened:** Closed TD-003 by adding a `--repo-root` parameter to `parse_identity.py` so that `file_path` in parser output is resolved relative to a deterministic repository root rather than the caller's current working directory. Threaded the parameter through `validator_runner.py` (both the Python API and CLI), `Run-Validator.ps1`, and `Promote-ToVerified.ps1`. The fix is backward-compatible: when `--repo-root` is omitted, the parser falls back to the previous `os.path.relpath()` behavior, so the existing test harness runs without modification.

**Why this matters:** The previous cwd-relative identity meant the same article produced different `file_path` values (and therefore different transaction keys, ledger entries, and hash-lock identifiers) depending on where the orchestration process was launched. This broke the governance contract's hash-lock invariant: a declined PR recorded under one transaction key could be bypassed by re-running from a different directory. With `--repo-root`, all three orchestration callers (`Run-Validator.ps1`, `Promote-ToVerified.ps1`, and `validator_runner.py` CLI) now produce identical repo-relative paths regardless of working directory.

**Artifacts:**
- pipeline/parse_identity.py — added `repo_root` parameter to `extract_frontmatter()` and `_to_repo_relative()`, added `--repo-root` CLI argument via argparse (replaces positional-only argv parsing)
- pipeline/validator_runner.py — added `repo_root` parameter to `run_parser()`, `run()`, and CLI `--repo-root` argument
- pipeline/Run-Validator.ps1 — passes `--repo-root $RepoRoot` to both parser and validator calls
- pipeline/Promote-ToVerified.ps1 — passes `--repo-root $RepoRoot` to parser call

**Key findings:**
- The bug was demonstrable: from the repo root, `parse_identity.py A-001.md` produced `pipeline/tests/golden_corpus/approve/A-001-clean-article.md`; from `/tmp`, the same file produced `../sessions/.../A-001-clean-article.md`. With `--repo-root`, both produce `pipeline/tests/golden_corpus/approve/A-001-clean-article.md`.
- The test harness intentionally does not pass `--repo-root` — corpus tests check decisions and exit codes, not `file_path` values, so the legacy behavior is harmless in that context and avoids coupling tests to a specific directory layout.
- Six additional gaps were identified during the review that produced this fix (see Gap Analysis below).

**Gap analysis surfaced during review:**
1. **TD-003 (this fix):** Repo-relative identity was cwd-dependent — now closed.
2. **Ledger writes are last-write-wins:** `Run-Validator.ps1` uses `Set-Content` (overwrite) for ledger entries keyed by transaction-key hash. Re-evaluating the same article under the same context silently clobbers the prior ledger record. JSONL telemetry is append-only and unaffected.
3. **No declined-PR hash-lock check:** Governance Invariant 6 specifies that `declined_by_human` hash/digest pairs must not be re-promoted. No runtime check exists yet — the lock is specified but not enforced.
4. **Promote-ToVerified.ps1 is not gated on validator decision:** The promotion script accepts an article path but has no mechanism to verify that the validator approved it. `Run-Validator.ps1` does not call promotion at all yet.
5. **`system_instruction_hash` in validator_config.json is static:** The hash was set at file creation and is not recomputed at runtime. If `SYSTEM_PROMPT.md` changes, the config's hash drifts silently. The context digest hashes the file separately, partially mitigating this.
6. **Cross-reference links in wiki pages use absolute Windows user-home paths** — these do not resolve in Obsidian or on other machines (fixed in Phase 1.1).

**Test count:** 166/166 baseline preserved — parser harness 37/37, validator harness 129/129. Zero regressions. Additional smoke test confirmed deterministic repo-relative identity from multiple working directories.
**Status:** TD-003 closed. Remaining open debt: TD-001 (live provider), TD-002 (Gitea promotion), TD-004 (documentation alignment). New gaps 2–6 above are recommended for tracking.

### Phase 1.1 — Governance Enforcement & Link Hygiene (April 8, 2026)

**What happened:** Closed four gaps identified during the Phase 1.0 review. Made ledger writes append-only by adding UTC timestamps (sub-second precision) to filenames, preventing silent overwrites on re-evaluation. Implemented the declined-PR hash-lock check (Governance Invariant 6) with fault-tolerant ledger scanning and match-detail returns for audit traceability. Gated promotion calls on validator approval, placed after ledger write to preserve the primary audit trail regardless of promotion outcome. Fixed absolute Windows paths in Governance/ and Program-Management/ wiki pages to use relative links compatible with Obsidian and portable environments.

**Artifacts:**
- pipeline/Run-Validator.ps1 — `Get-SafeLedgerName` now produces sub-second timestamped filenames; added `Test-DeclinedHashLock` with try/catch per entry and structured return object; added promotion gate after ledger write with fault logging
- handoff/Run-Validator.ps1 — synced to match pipeline copy
- Governance/Human-in-the-Loop Governance.md — 7 cross-reference links converted from absolute Windows paths to relative
- Program-Management/Program Management for Technical Infrastructure.md — 5 cross-reference links converted from absolute Windows paths to relative

**Key findings:**
- The ledger overwrite was a real governance violation: re-evaluating the same article under identical conditions silently destroyed the prior record, making it impossible to reconstruct decision history for DPO training or audit.
- The hash-lock check is a ledger-side enforcement that does not require Gitea. It can be implemented and tested now against the existing external state, independent of remote promotion wiring.
- Placing promotion after ledger write means an approved evaluation is durable even if promotion fails. The fail-closed `Promote-ToVerified.ps1` now throws on every non-DryRun approve, logged as `promotion_gated_pending_remote_wiring` with FMEA ref F7.
- DryRun does not bypass the hash-lock — Invariant 6 is unconditional per the governance contract.

**Test count:** 166/166 baseline preserved (verified this session) — parser harness 37/37, validator harness 129/129. Harness tests parser and validator modules directly; `Run-Validator.ps1` changes are orchestration-layer logic not covered by the golden corpus harness.
**Status:** Gaps 1–4 from Phase 1.0 review closed in both pipeline and handoff. Remaining open debt: TD-001 (High: live provider), TD-002 (High: Gitea promotion), TD-004 (Low: documentation alignment). Gap #5 (static `system_instruction_hash`) deferred — partially mitigated by context digest hashing the actual file.

### Phase 1.2 — Adversarial Corpus Expansion & Null Source-ID Fix (April 8, 2026)

**What happened:** Expanded the golden corpus from 30 to 42 fixtures by adding 12 adversarial test cases covering three previously untested categories: LLM response parsing (5 fixtures), YAML edge cases (2 fixtures), frontmatter type-coercion bugs (2 fixtures), and content/policy detection depth (3 fixtures). Fixed a null source_id bug in `parse_identity.py` where YAML `null` slipped through the identity regex as the string `"None"` — the parser now rejects null before `str()` coercion. Added a regression test fixture (ADV-021) to prevent recurrence.

**Why this matters:** The Phase 0 corpus tested parser failures and LLM policy decisions, but had zero coverage for the validator's response-parsing pipeline (SCHEMA_FAULT, exit code 3). Fixtures ADV-015 through ADV-019 close that gap by exercising fence stripping, missing required fields, invalid enums, extra properties, and empty responses. The YAML edge cases (anchors, duplicate keys) document known safe_load behavior that was previously assumed but untested. The content fixtures (ADV-024 subtle PII in code, ADV-025 sandwich injection, ADV-026 mixed-severity cascade) add structural variety to security and accuracy coverage.

**Artifacts:**
- pipeline/parse_identity.py — null source_id rejection before str() coercion
- pipeline/tests/golden_corpus/adversarial/ADV-015 through ADV-026 (12 article files)
- pipeline/tests/golden_corpus/responses/ADV-015 through ADV-026 (10 canned response files; ADV-021 and ADV-022 are parser-stage, no responses needed)
- pipeline/tests/golden_corpus/corpus_manifest.json — updated with 12 new fixture entries
- pipeline/tests/golden_corpus/CORPUS_MANIFEST.md — updated fixture tables and coverage summary
- strategy/GOLDEN_CORPUS_COVERAGE_MAP.md — version 1.1, updated matrix, parser enforcement summary, growth targets

**Key findings:**
- Two response files (ADV-024, ADV-026) initially used incorrect schema fields (`code`/`detail`/`location` instead of `rule_id`/`description`/`severity`). The harness's eager schema validation caught both before any test ran — demonstrating the value of the validation gate.
- Running `--stage all` produces 196 passed / 0 failed assertions (51 parser + 145 validator, deduplicated). Running stages separately: 51 parser + 177 validator = 228 total. The difference is parser assertions that overlap in the validator stage.
- The adversarial ratio is now 61.9% (26/42), well above the 30% CORPUS_MAINTENANCE_SOP floor. The next calibration round should prioritize non-adversarial fixtures to balance toward ~40%.
- ADV-015 (markdown-fenced response) confirmed that `parse_llm_response()` correctly strips ``` fences — a positive test for an important production code path that had no coverage.

**Test count:** 196/196 assertions passing (`--stage all`). Parser harness 51/51, validator harness 177/177. Integration stage (CTX-001) remains intentionally unimplemented.
**Status:** Corpus expansion complete. Remaining open debt unchanged: TD-001 (live provider), TD-002 (Gitea promotion), TD-004 (documentation alignment). Next recommended work is non-adversarial calibration fixtures (to rebalance the adversarial ratio) or provider decision (OQ-1).

### Phase 1.3 — Live Provider Wiring: Anthropic (April 8, 2026)

**What happened:** Resolved OQ-1 (provider selection) by choosing Anthropic Claude Sonnet 4.6 as the initial managed-API primary evaluation path. Implemented a live provider branch in `validator_runner.py`, updated `validator_config.json` to target `anthropic` / `claude-sonnet-4-6`, and replaced the unconditional stub override in `Run-Validator.ps1` with credential-aware fallback logic. The stub path is preserved as a valid provider for testing and environments without API credentials.

**Why Anthropic over Vertex AI:** The architecture (ADR-002) supports any managed-API provider — Vertex AI, OpenAI, or Anthropic — behind the same provider abstraction. The infrastructure state on this machine favored Anthropic: `ANTHROPIC_API_KEY` is present in the environment while GCP/Vertex AI credentials are not configured locally. The provider abstraction in `validator_runner.py:263` (injectable callable) means switching to Vertex AI later is a config change plus one new provider function, not a redesign.

**Artifacts:**
- pipeline/ops/validator_config.json — `provider` changed from `vertex_ai` to `anthropic`; `model_id` changed from `gemini-1.5-pro` to `claude-sonnet-4-6`; `tokenizer_id` changed from `gemini-1.5-pro` to `claude-sonnet-4-6`; all other fields unchanged
- pipeline/validator_runner.py — added `import os`, `import time`; added LLM-specific constants (`LLM_TIMEOUT_SECONDS`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_RETRY_ATTEMPTS`, `LLM_RETRY_DELAY_SECONDS`); added `anthropic` branch in `default_provider()`; added `_anthropic_provider()` with lazy SDK import, env-var auth, single retry on transient errors (rate limit, overload, connection), no retry on auth/bad-request, text extraction from Messages API content blocks; updated `vertex_ai` error message to reference `anthropic` as alternative
- pipeline/Run-Validator.ps1 — replaced unconditional stub override in `Get-EffectiveValidatorConfigObject` with credential-aware fallback: `anthropic` passes through when `ANTHROPIC_API_KEY` is set, falls back to stub with warning when absent; `vertex_ai` still falls back to stub (unimplemented)

**Key findings:**
- The golden corpus harness (196/196) is unaffected because it uses its own inline config (`provider: "harness"`) and injects a `corpus_provider` callable that bypasses `default_provider()` entirely. The harness exit code remains 3 (integration stage unimplemented), not 0.
- The live Anthropic path requires `pip install anthropic`. The SDK import is lazy (inside `_anthropic_provider()`) so its absence does not break stub or harness paths.
- Token budgeting still uses the generic `BYTES_PER_TOKEN_ESTIMATE = 4` heuristic rather than a model-specific tokenizer. This does not yet satisfy the Strategy Kit's requirement (Section 7.2) that budget checks use the active model's tokenizer. TD-001 remains open with narrowed scope for this reason.
- The config change from `vertex_ai` to `anthropic` correctly invalidates all prior context digests (via `Run-Validator.ps1` `Get-ContextDigest`), which is the desired behavior when switching providers.

**Test count:** 196/196 baseline preserved (harness-verified). Parser harness 51/51, validator harness 177/177. Harness exit code 3 (integration stage unimplemented). Live provider path not yet smoke-tested (requires SDK install and provisional article).
**Status:** OQ-1 resolved. Live provider path exists but not yet exercised. TD-001 narrowed from "no live provider" to "token budgeting uses generic estimate, not model-specific tokenizer." Next steps: install SDK, smoke-test against a real article, then proceed to corpus rebalancing.

### Phase 1.4 — Non-Adversarial Corpus Calibration Rebalance (April 8, 2026)

**What happened:** Added 8 non-adversarial fixtures to the golden corpus, expanding from 42 to 50 total fixtures and reducing the adversarial ratio from 61.9% to 52.0%. Closed the two named coverage gaps (FORMATTING-001 and ACCURACY-004 non-escalation) identified in GOLDEN_CORPUS_COVERAGE_MAP.md. All 15 violation rule IDs in VIOLATION_TAXONOMY.md are now exercised by at least one dedicated fixture.

**Why this matters:** The adversarial ratio was 61.9% after Phase 1.2, well above the ~47–53% target for the next calibration round (GOLDEN_CORPUS_COVERAGE_MAP.md growth targets). Calibration quality skews toward edge cases when the corpus over-represents adversarial fixtures. The 8 new non-adversarial fixtures deepen the normal approve/reject/escalate paths that will be most exercised during live-provider calibration.

**Artifacts:**
- pipeline/tests/golden_corpus/approve/A-008-missing-h1-heading.md — closes FORMATTING-001 desert (approve with minor formatting observation)
- pipeline/tests/golden_corpus/approve/A-009-unsourced-performance-claim.md — closes ACCURACY-004 non-escalation gap (approve with minor accuracy observation)
- pipeline/tests/golden_corpus/approve/A-010-git-branching.md — clean approve, development-workflow domain
- pipeline/tests/golden_corpus/approve/A-011-structured-logging.md — clean approve, observability domain
- pipeline/tests/golden_corpus/reject/R-006-todo-placeholders.md — COMPLETENESS-001 + COMPLETENESS-003 (CI/CD guide with TODOs and stubs)
- pipeline/tests/golden_corpus/reject/R-007-wrong-status-codes.md — ACCURACY-001 + ACCURACY-005 (HTTP status codes systematically wrong)
- pipeline/tests/golden_corpus/escalate/E-004-oversimplified-architecture.md — ACCURACY-003 primary + NEUTRALITY-001 secondary (microservices oversimplification)
- pipeline/tests/golden_corpus/escalate/E-005-borderline-stale-tooling.md — ACCURACY-002 borderline (Node.js 18 LTS approaching EOL)
- pipeline/tests/golden_corpus/responses/ (8 new canned responses: A-008 through A-011, R-006, R-007, E-004, E-005)
- pipeline/tests/golden_corpus/corpus_manifest.json — updated with 8 new fixture entries (50 total)
- pipeline/tests/golden_corpus/CORPUS_MANIFEST.md — updated fixture tables and coverage summary
- strategy/GOLDEN_CORPUS_COVERAGE_MAP.md — version 1.2, updated matrix, closed deserts, revised growth targets

**Key findings:**
- Running `--stage all` produces 244 passed / 0 failed assertions (59 parser + 225 validator, deduplicated to 244). Running stages separately: 59 parser + 225 validator = 284 total. The difference is parser assertions that overlap in the validator stage.
- The adversarial ratio is now 52.0% (26/50), inside the documented 47–53% target range. The next expansion round should continue moving toward the ~40% parity-harness-ready target.
- All 15 violation rule IDs in the taxonomy are now exercised. No remaining testing deserts at the rule-ID level. Remaining work is depth-building (additional fixture shapes per rule) rather than gap closure.
- E-005 (borderline ACCURACY-002) is a genuinely ambiguous case: Node.js 18 is in maintenance mode approaching EOL, not yet past it. The escalation decision reflects the governance framework's distinction between clear reject (R-004 pattern) and edge cases that warrant editorial judgment.

**Test count:** 244/244 assertions passing (`--stage all`). Parser harness 59/59, validator harness 225/225. Integration stage (CTX-001) remains intentionally unimplemented. Harness exit code 3.
**Status:** Calibration rebalance complete. All named gaps closed. Next steps: smoke-test live Anthropic provider path, then TD-002 (Gitea promotion).

### Phase 1.6 — Live Provider Smoke Test (April 26, 2026)

**What happened:** First end-to-end live API call through the production validator path. Staged a clean Kubernetes networking fixture (sourced from `pipeline/tests/golden_corpus/approve/A-001-clean-article.md`) into `pipeline/provisional/A-001-smoke-test.md` with a unique `source_id` (`A-001-smoke-2026-04-26`), then ran `Run-Validator.ps1` against the live Anthropic Claude Sonnet 4.6 endpoint with `provider: "anthropic"` from the production `validator_config.json`. The validator returned a schema-valid `approve` decision (confidence `0.91`), wrote a ledger entry to `C:\llm-wiki-state\ledger\`, and emitted four JSONL events (`run_started`, `operational_fault` from the F7 promotion gate, `evaluation_completed`, `run_completed`). End-to-end wall-clock latency was 8.16 seconds for one article including count_tokens preflight, Messages API call, ledger write, and the gated promotion attempt.

**Why this matters:** TD-001 was closed in Phase 1.5 with the live Anthropic provider wired and a model-specific tokenizer in place, but the path had never been exercised against a real article. This smoke test confirms the SDK integration works end-to-end, the schema validation gate passes on real model output, and the ledger captures a faithful, schema-valid record. It also produces the first live-provider audit baseline that future regression tests and DPO preference pairs can reference.

**Artifacts:**
- Ledger entry `f3f321a6cc17…_20260427T011133…Z.json` under `C:\llm-wiki-state\ledger\` (3,364 bytes; runtime audit history, not committed)
- JSONL events appended to `C:\llm-wiki-state\logs\pipeline.log`: `run_started`, `operational_fault` (F7), `evaluation_completed`, `run_completed`
- `pipeline/provisional/A-001-smoke-test.md` — transient, deleted post-run per smoke-test cleanup; not committed
- `README.md` — Roadmap item 1 marked complete; Phase 1.6 follow-up items added; status table updated
- `PROJECT_LEDGER.md` — this entry; cumulative metrics updated

**Key findings:**
- The live model returned a clean approve with substantive reasoning (factual accuracy, structural completeness, no security/PII concerns) and three actionable recommendations (CNI plugin tradeoffs, link to upstream Kubernetes networking docs, suggestion to cover Ingress / Gateway API). Confidence `0.91` aligns with a clean approve under a conservative reviewer policy.
- The model correctly followed the SYSTEM_PROMPT contract for clean approvals: `policy_violations: []` even though the `reasoning` text mentions a NEUTRALITY-001 observation. Info-level observations were folded into `recommendations` rather than the structured array, consistent with the policy bundle (NEUTRALITY-001 is `info` severity, observational only). This is the intended calibration behavior, and matches how the deterministic stub responses are shaped in the golden corpus.
- `article_token_count` in the ledger entry is `null`. The token count is computed during `check_token_budget()` inside `validator_runner.py` via `count_tokens_for_provider()`, which dispatches to `count_tokens_anthropic` (Anthropic Messages API `count_tokens` endpoint) when provider=anthropic with the API key present, and falls back to byte estimate otherwise. No fallback warning was emitted in stderr during this run, so the live-tokenizer path is **inferred** to have succeeded — but the method choice is not directly logged on success, only on fallback. Recommended follow-ups: (a) thread the count back from the validator to the orchestration layer for ledger inclusion, (b) emit a single positive `INFO: token_method=... input_tokens=...` line on every run so future smoke tests have explicit evidence rather than inferring from the absence of a warning.
- Encountered a real portability gap during the smoke test: `Run-Validator.ps1` contains four em-dash characters (`—`, U+2014) in comments and warning strings, and is saved as UTF-8 without BOM. Windows PowerShell 5.1 reads scripts as Windows-1252 by default, which mis-parses these em-dashes and breaks the `Get-EffectiveValidatorConfigObject` function with `MissingEndCurlyBrace`. PowerShell 7+ (`pwsh`) handles UTF-8 natively and parses cleanly. The smoke test was completed via `pwsh`. Recommended follow-up: replace em-dashes with ASCII hyphens or save the script with UTF-8 BOM so PS5.1 also parses correctly.
- The F7 promotion gate fired as expected (TD-002 fail-closed), confirming the gate placement after ledger write preserves the audit trail even when downstream promotion is unavailable. The decision is durably recorded in the ledger; the promotion attempt is a separate concern, logged as `promotion_gated_pending_remote_wiring` with `fmea_ref: F7`. The promotion preview audit file (`C:\llm-wiki-state\audit\promotion-preview-c9269825ecdb.json`, 745 bytes) was confirmed on disk after the run, demonstrating that the fail-closed branch in `Promote-ToVerified.ps1` still produces durable audit evidence even when the live PR path is unavailable.
- The `model_config_snapshot` in the ledger faithfully captures the runtime config (`provider: anthropic`, `model_id: claude-sonnet-4-6`, `temperature: 0.0`, matching `system_instruction_hash`), and the `context_digest` (`954ea34e…`) reflects the live-provider config — confirming the Phase 0.8 integrity fix where the effective config used at runtime is also the config reflected in the digest.

**Limitations of this smoke test:**
- Only the **approve happy path** was exercised. Reject, escalate, token-overflow, and transient API-error paths remain untested live; they continue to be covered only by the deterministic stub harness.
- **Determinism at `temperature: 0.0` was not verified.** A repeat call with the same input was not made; the smoke test produces one observation, not a determinism check.
- **Wall-clock latency (8.16 s) is end-to-end for the entire script**, including parser invocation, the `count_tokens` preflight network call, the Messages API call, schema validation, ledger write, and the failed promotion attempt. It is not a clean Anthropic round-trip number; per-stage timing is not currently captured.
- **The token-count method is inferred, not logged** on success (see ledger surface follow-up above).
- The smoke-test article was placed in `pipeline/provisional/`, which is **not gitignored** at the article level — only manual cleanup before staging prevented the transient article from entering git history. Recommended follow-up: add a `*-smoke-test*.md` ignore pattern under `pipeline/provisional/`, or stage smoke runs to a gitignored `pipeline/.smoke/` location, so future smoke tests are safe against accidental commits.

**Test count:** 244/244 assertions passing (`--stage all`) — parser harness 59/59, validator harness 225/225. Verified before and after the live run. Integration stage remains intentionally unimplemented (exit 3).
**Status:** README Roadmap item 1 closed. Phase 1.6 produced the first live-provider audit baseline. New observations surfaced for follow-up: (a) `article_token_count` ledger surface gap, (b) `Run-Validator.ps1` em-dash portability gap on PS5.1.

---

## Decision Log

### ADR-001: Trust-Nothing Control Plane (April 5, 2026)
**Decision:** Adopt a four-component control plane with deterministic transaction identity, composite context digests, PR-gated promotion, and externalized state.
**Why:** LLM output is inherently non-deterministic. Every boundary must validate independently. External state prevents metadata from polluting the content repository.
**Trade-off:** Higher implementation complexity than a simpler pass/fail pipeline. PowerShell + Python cross-layer boundary requires explicit exit code testing.
**Status:** Active

### ADR-002: Hybrid Deployment Model (April 6, 2026)
**Decision:** Managed API (Vertex AI / OpenAI / Anthropic) as primary evaluation path, self-hosted open model (Llama, Mistral) as secondary path gated by runtime parity harness.
**Why:** Single-provider assumption creates vendor lock-in and cost risk. Self-hosted path enables future fine-tuning (LoRA/DPO) without redesign.
**Trade-off:** Requires token budgeting per model (different tokenizers), parity testing infrastructure, and fallback semantics.
**Status:** Active

### ADR-003: Log Now, Build Later (April 6, 2026)
**Decision:** Retain full structured evaluation payloads in the ledger from day one (P0-14). LoRA/QLoRA and DPO are LATER-phase capabilities.
**Why:** DPO and LoRA should influence what you log now, but not what you build now. Preference pairs (merged PR = positive, declined PR = negative) require the full evaluation context to be useful.
**Trade-off:** Larger ledger storage from day one. Retention schema must be designed upfront even though training is deferred.
**Status:** Active

### ADR-004: Anthropic as Initial Managed-API Provider (April 8, 2026)
**Decision:** Use Anthropic Claude Sonnet 4.6 as the initial managed-API primary evaluation path, with Vertex AI (Gemini) deferred to a future provider expansion.
**Why:** ADR-002 established a hybrid deployment model supporting multiple managed-API providers. The provider abstraction in `validator_runner.py` isolates the pipeline from API specifics — the evaluator only needs a callable that takes a payload dict and config dict and returns a JSON string. Anthropic was chosen for the initial wiring because credentials were available in the current environment, the API structure (system + messages) maps directly to the existing payload format, and Sonnet 4.6 provides the right latency/cost profile for iterative calibration of a structured policy-judgment task.
**Trade-off:** The config and documentation were originally written around Vertex AI. Switching the config to `anthropic` is a clean break (context digests correctly invalidate), but documentation references to Vertex AI in the Strategy Kit now describe the intended future state rather than the current runtime. Adding Vertex AI later is a config change plus one new provider function.
**Status:** Active

---

## Cumulative Metrics

| Metric | Phase 0 | Current |
|--------|---------|---------|
| **Tests passing** | 0 | 244/244 (59 parser + 225 validator; 244 deduplicated via `--stage all`) |
| **Source files** | 0 (design only) | 12 core runtime/test artifacts (parser, schemas/helpers, harness, production validator, runtime bootstrap, prompt, policy bundle) |
| **Pipeline components** | 0 / 4 | 4 / 4 artifacts present (parser complete; production validator with live Anthropic provider; orchestration with credential-aware fallback; promotion preflight present) |
| **Live provider** | — | Anthropic Claude Sonnet 4.6 (smoke-tested Phase 1.6: decision=`approve`, confidence `0.91`, ~8.2s end-to-end) |
| **Golden corpus fixtures** | 0 | 50 (11A/7R/5E/26Adv/1Int) — all 15 violation rule IDs exercised; 52.0% adversarial ratio |
| **Testing deserts** | — | 0 at rule-ID level; remaining work is depth-building per rule |
| **Specification artifacts** | 0 | 13 (6 strategy specs + 7 contract wiki pages) |
| **FMEA failure modes** | 17 defined | 0 at High residual risk |
| **Strategy Kit rev** | 3.4 | 3.4 |

---

## Technical Debt Register

| ID | Description | Severity | Introduced | Status |
|----|-------------|----------|------------|--------|
| TD-001 | Live Anthropic provider path wired (Phase 1.3). Model-specific tokenizer implemented (Phase 1.5): `count_tokens_for_provider()` dispatches to Anthropic Messages API `count_tokens` endpoint when provider=anthropic and API key is available; falls back to conservative byte estimate (4 bytes/token) for stub provider or when SDK/key unavailable. Response reserve (2048 tokens) applied per Strategy Kit 7.2. Token overflow diagnostic now includes input count, budget, method used. | Low | Phase 0.6 | **Closed** (Phase 1.5) |
| TD-002 | `Promote-ToVerified.ps1` Gitea integration partially implemented (Phase 1.5): env-driven client layer, conservative declined-PR reconciliation with correct composite context_digest, preflight startup cleanup, branch-existence check (fail-closed). OQ-2 resolved — branch protection confirmed (`enable_push=false`, `required_approvals=1`) on an external Gitea instance (private, not included in this repository). Gitea credential flow validated locally; credentials are not stored in this repository. Remaining gaps: full tree-SHA equivalence (P0-8 — requires git/trees API or local fetch), live git push + PR creation path (commented out, ready to activate), workspace rollback for live promotion side effects | Medium | Phase 0.6 | **Narrowed** (Phase 1.5) |
| TD-003 | `parse_identity.py` still resolves `file_path` via current working directory rather than deterministic repo-root-relative identity | Medium | Phase 0.6 | **Closed** (Phase 1.0) |
| TD-004 | README drift was reduced on April 7, 2026, but documentation alignment still needs a broader audit across portfolio entry points | Low | Phase 0.6 | Open |

---

*Ledger maintained by: Josh Hillard*
*Last updated: April 26, 2026 (Phase 1.6 — Live Provider Smoke Test)*
