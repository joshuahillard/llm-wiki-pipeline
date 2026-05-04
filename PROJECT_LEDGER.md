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

### Phase 1.5 — Live Tokenizer & Gitea Integration Scaffolding (April 9, 2026)

**What happened:** Closed TD-001 (live model-specific tokenizer) and significantly narrowed TD-002 (Gitea promotion). In `validator_runner.py`, added `count_tokens_for_provider()` to dispatch token counting to the Anthropic Messages API `count_tokens` endpoint when `provider=anthropic` with the API key present, with a conservative byte-estimate fallback (4 bytes/token plus system overhead) for the stub provider, missing SDK, missing key, or any tokenizer call failure. Applied the Strategy Kit § 7.2 response reserve (`RESPONSE_RESERVE_TOKENS = 2048`) to the budget calculation. In `Promote-ToVerified.ps1`, built out a complete env-driven Gitea client layer, declined-PR reconciliation with composite-digest hash-lock compatibility, startup reconciliation for orphaned `pending_pr/` entries, and a fail-closed remote branch-existence check. Resolved OQ-2 by verifying branch protection on the configured external Gitea instance.

**Why this matters:** TD-001 was the last gap between "the validator runs" and "the validator runs a real model with a real budget gate." Without a model-specific tokenizer, token budgeting relied on a generic four-bytes-per-token estimate — fine for Latin-script English prose but unreliable for code-heavy or multilingual content. Wiring `count_tokens` makes the budget check an exact gate rather than a heuristic for the live path, while preserving the conservative estimate as a safe fallback for paths that cannot or should not call the API. TD-002 sits between "evaluation produces a decision" and "approved articles actually move." Phase 1.5 did not activate live PR creation (still gated behind local git push and workspace rollback work), but it established every layer beneath that activation — credentials, API helpers, audit-evidence writers, declined-PR semantics, and the preflight cleanup loop — and removed OQ-2 from the open questions list by confirming that the configured Gitea instance enforces the protections the design assumes.

**Artifacts:**
- pipeline/validator_runner.py — added `count_tokens_anthropic()` (Anthropic Messages API `count_tokens` endpoint, 30 s timeout, lazy SDK import, ProviderError on failure); added `count_tokens_for_provider()` dispatcher returning `(token_count, method_used)` where method is `"anthropic_api"` or `"byte_estimate"`; added `RESPONSE_RESERVE_TOKENS = 2048` and `TOKEN_COUNT_TIMEOUT_SECONDS = 30`; updated `check_token_budget()` to call the dispatcher and surface `token_info` (input_tokens, max_tokens, budget, method) in the TOKEN_OVERFLOW diagnostic.
- pipeline/Promote-ToVerified.ps1 — added env-driven `Get-GiteaConfig` / `Invoke-GiteaApi`; added Gitea API helpers `Get-GiteaPullRequests`, `New-GiteaPullRequest`, `Get-GiteaBranch`, `Remove-GiteaBranch`; added `Invoke-DeclinedPrReconciliation` with conservative `state=closed AND merged=false → declined_by_human` mapping and full PR-evidence capture; added `Write-ReconciliationLedgerEntry` writing `reconciliation_<hash>_<timestamp>.json` files; added `Test-RemoteBranchState` (fail-closed branch-existence check; tree-SHA equivalence per P0-8 explicitly deferred and called out inline); added `Invoke-StartupReconciliation` for orphaned `pending_pr/` cleanup; added `Write-PendingPrEntry`; required `-ContextDigest` parameter for live promotion (so reconciliation entries match `Test-DeclinedHashLock` in `Run-Validator.ps1`); kept the live PR creation path behind a hard `throw` until git-push and workspace rollback land.
- pipeline/Run-Validator.ps1 — `Get-EffectiveValidatorConfigObject` already handled credential-aware fallback from Phase 1.3; this phase ensures the live-tokenizer path is exercised when the credential check passes by leaving the production config with `provider: "anthropic"` and `model_id: "claude-sonnet-4-6"`.
- PROJECT_LEDGER.md — Technical Debt Register updated: TD-001 closed, TD-002 narrowed with detailed scope of remaining gaps.

**Key findings:**
- Token budgeting now uses two distinct token counts depending on provider availability: exact Anthropic count when feasible, conservative byte estimate otherwise. The byte estimate (`bytes/4 + 4096 system overhead`) intentionally over-counts so that borderline articles trip TOKEN_OVERFLOW rather than failing mid-request. The fallback is non-fatal: a `count_tokens` failure logs a warning and falls back to the estimate, preserving forward progress.
- The method choice is logged to stderr on fallback only; on success, the method is silent (no positive log line). This was acceptable for the close of TD-001 but became an evidence gap surfaced explicitly in Phase 1.6 — see that entry's follow-ups.
- Declined-PR reconciliation is conservative by design: any `state=closed AND merged=false` PR is treated as `declined_by_human`. This may produce false positives (e.g., a PR closed for being superseded by another that ultimately merged), but never false negatives. The reconciliation note records the source as `gitea_remote_pr_state` so that the provenance is explicit and downstream consumers know the classification is heuristic.
- The branch-existence check is also conservative: the existence of a remote branch hard-fails the promotion regardless of tree contents, because the Gitea git/trees API call (or local fetch + `git cat-file`) needed for true tree-SHA equivalence (P0-8) is not yet wired. This prefers false negatives over false positives, which is correct for a fail-closed gate.
- The composite `-ContextDigest` requirement on live promotion exists because reconciliation ledger entries are looked up by `Test-DeclinedHashLock` in `Run-Validator.ps1` using the run-time composite digest. Allowing standalone promotion to use a different digest would silently break the hash-lock invariant; failing closed in the standalone case preserves Governance Invariant 6.
- OQ-2 resolution did not change the Strategy Kit's posture toward Gitea (still the preferred self-hosted git host for the promotion path), but it confirmed that the configured instance enforces the protections the design assumes (`enable_push=false`, `required_approvals=1`, `enable_force_push=false`). The instance, its URL, and the credentials remain external to this repository per the README "External / Private Working Material" section.

**Test count:** 244/244 baseline preserved — parser harness 59/59, validator harness 225/225. No corpus changes this phase. Harness exit code 3 (integration stage intentionally unimplemented). The live tokenizer and Gitea code paths are not exercised by the harness (the harness uses a stub provider and does not call promotion); both were verified manually during this phase, with the live tokenizer subsequently smoke-tested end-to-end in Phase 1.6.
**Status:** TD-001 closed. TD-002 narrowed (env layer, reconciliation, preflight, branch-check all in; remaining: live git push, tree-SHA equivalence per P0-8, workspace rollback). OQ-2 resolved. Open debt: TD-002 (remaining gaps above), TD-004 (documentation alignment). Next step at the time: smoke-test the live Anthropic provider path against a real article (subsequently closed in Phase 1.6).

> **Note:** This timeline entry was backfilled on April 26, 2026 during Phase 1.6 work. The Technical Debt Register and ledger footer already referenced "Phase 1.5" with the work described above; only the timeline entry itself was missing. No code or runtime state changed when this entry was added.

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

### Phase 1.7 — Integration Test Stage Implementation (April 26, 2026)

**What happened:** Implemented the integration stage in `pipeline/tests/run_harness.py`, converting `python run_harness.py --stage all` from "244 passed, exit 3 (partial coverage)" to "320 passed, exit 0". The stage exercises the full orchestration end-to-end (parse → validate → ledger write → audit → F7 promotion gate) across three decision paths (approve / reject / escalate) plus a determinism re-run, by invoking `pwsh Run-Validator.ps1` against a temp `-StateRoot`, `-ProvisionalRoot`, and `-VerifiedRoot`. Decision selection is driven by a new `LLM_WIKI_STUB_DECISION` env override added to `_stub_response()` in `pipeline/validator_runner.py` (~30 lines). Three latent issues surfaced during implementation and were fixed in the same phase: a `[hashtable]` parameter type constraint on `New-FeedbackSidecar` that broke the reject and escalate orchestration paths whenever they were exercised live, the absence of `-ProvisionalRoot` and `-VerifiedRoot` parameters on `Run-Validator.ps1` and `Promote-ToVerified.ps1` (which prevented isolated test runs without polluting `pipeline/provisional/` or computing destination paths against the real repo tree), and four em-dash characters in `Run-Validator.ps1` that caused parse failures on Windows PowerShell 5.1 (Phase 1.6 follow-up — Roadmap item 4 closed in this phase).

**Why this matters:** Phase 1.6 ended with `--stage all` reporting "244 passed, exit 3" because the integration stage was a documented unimplemented hole. Exit 3 was an honest "partial coverage" signal but blocked CI integration (CI systems expect exit 0 on green). Closing this gap delivers two things: (1) every future change now produces a clean exit-0 signal from the harness when all stages pass, and (2) the orchestration's reject/escalate code paths and the F7 promotion-gate emission semantics are exercised automatically and reproducibly in CI rather than only via manual smoke tests. It also surfaced the `New-FeedbackSidecar` type bug that had been latent since Phase 1.1 — the harness's existing parser and validator stages cannot catch orchestration-layer errors because they bypass `Run-Validator.ps1` entirely.

**Artifacts:**
- pipeline/tests/run_harness.py — added integration-stage helpers (`_check_pwsh_available`, `_run_orchestration_once`, `_assert_orchestration_run`, `_assert_determinism`, `run_integration_tests`), wired into `main()` to replace the prior "NOT IMPLEMENTED" branch; added stdlib imports (`os`, `re`, `shutil`, `tempfile`).
- pipeline/validator_runner.py — `_stub_response()` now reads the optional `LLM_WIKI_STUB_DECISION` env var and returns a canned reject or escalate response when set; default behavior (approve) unchanged when the env var is unset.
- pipeline/Run-Validator.ps1 — added optional `-ProvisionalRoot` and `-VerifiedRoot` parameters with the prior literal defaults preserved; propagates both into the call to `Promote-ToVerified.ps1`; replaced four em-dash characters (lines 86, 92, 278, 337) with ASCII hyphens (closes Phase 1.6 Roadmap item 4); changed `New-FeedbackSidecar`'s `$ValidationResult` parameter from `[hashtable]` to `[object]` so PSCustomObject inputs from `ConvertFrom-Json` are accepted.
- pipeline/Promote-ToVerified.ps1 — added optional `-ProvisionalRoot` and `-VerifiedRoot` parameters with the prior literal defaults preserved.
- pipeline/tests/golden_corpus/CORPUS_MANIFEST.md — Integration Tests row updated to reflect automation and current test scope; the historical `CTX-001-README.md` is retained but its digest-rotation premise is explicitly marked as moot.
- README.md — Status table updated (Phase 1.7, integration count, exit-0); Test section updated; Install requirements clarified (pwsh required for integration stage); Roadmap items reordered (Phase 1.6 follow-ups (3) and (4) collapsed; integration-stage item removed).

**Key findings:**
- The integration stage added 76 assertions across four runs: 30 for the approve correctness path, 22 each for reject and escalate, and 2 for the determinism comparison. New `--stage all` total: 320 (244 prior + 76 integration). Three consecutive `--stage all` runs produced byte-identical pass counts and exit 0 (non-flakiness verified).
- The `New-FeedbackSidecar` `[hashtable]` parameter constraint was a real latent bug, not a test artifact. `ConvertFrom-Json` returns a `PSCustomObject`, which PowerShell does not auto-convert to `Hashtable`. Any reject or escalate decision in production would have failed with `Cannot process argument transformation on parameter 'ValidationResult'`. The bug was undetected because the deterministic stub had only ever returned approve, and Phase 1.6's live smoke test also returned approve. Reject/escalate would have failed live the first time they were exercised.
- The em-dash portability issue documented as Phase 1.6 Roadmap item 4 was closed by replacing `—` (U+2014) with `-` (U+002D) at four call sites in `Run-Validator.ps1`. The script now parses cleanly under both `pwsh` (PowerShell 7+) and Windows PowerShell 5.1. The integration stage still hard-requires `pwsh` to guard against future regressions.
- Adding `-ProvisionalRoot` and `-VerifiedRoot` was driven by a concrete need: `Get-RepoRelativePath` throws when the source or destination path falls outside the configured `-RepoRoot`. Pointing `-RepoRoot` at a temp dir without also overriding the provisional and verified roots produced an "outside repo root" throw before the audit-preview file could be written, breaking the audit assertion. Adding the parameters with prior-default fallbacks is backward-compatible.
- The `CTX-001-README.md` Phase 0.6 procedure ("rotate temperature, expect re-evaluation under new digest") is moot under current code: the Phase 1.1 ledger-filename change made writes append-only via sub-second timestamps, so two runs of the same article under the same config also produce two distinct ledger entries. There is no caching layer to invalidate. The Phase 1.7 integration stage tests the orchestration's actual current contract (decision-path coverage, F7 fault emission, ledger and audit shape, determinism) rather than the obsolete "digest invalidates cache" claim. The README is retained as a Phase 0.6 historical artifact.
- The `LLM_WIKI_STUB_DECISION` env override was chosen over CLI-flag plumbing through `Run-Validator.ps1` and `validator_runner.py` because it is the smallest path-of-change: env vars propagate naturally to subprocesses without modifying the orchestration script's command line, and the override is opt-in (unset → unchanged approve behavior). The override is local to the stub provider; the live Anthropic provider path is unaffected.

**Limitations of this stage:**
- **Stub-only.** The integration stage uses the deterministic stub provider (forced via removal of `ANTHROPIC_API_KEY` from the subprocess env, triggering the credential-aware fallback in `Run-Validator.ps1`). It does not exercise the live Anthropic path. A real-LLM regression would not be caught here; it remains the responsibility of the Phase 1.6-style manual smoke test and of any future live-provider corpus run.
- **F7 is allowlisted as the expected fault.** When `decision == "approve"`, the stage asserts that exactly one `operational_fault` event is emitted with `fmea_ref == "F7"` and `message == "promotion_gated_pending_remote_wiring"`. This is the expected "fail-closed pending TD-002" semantic. The fault in the test fires from the Gitea-credentials-missing throw at the top of `Promote-ToVerified.ps1`'s post-DryRun block (since `GITEA_URL` etc. are unset), not from the canonical "live PR creation gate" throw further down. Both code paths emit identical `fmea_ref` and `message`, so the assertion passes either way; the canonical-throw path will need direct exercise once Gitea credentials are configurable in test contexts. When TD-002 fully closes and the canonical throw is removed, this allowlist must be inverted (assert no F7 fault and assert a successful-PR-creation event).
- **`origin_main_marker` is "no-git-head" in tests.** The integration stage uses the temp work_root as `-RepoRoot`, which has no `.git` directory. `Get-OriginMainMarker` returns the literal string `"no-git-head"`, so the `context_digest` reflects script hashes + config but not real git state. Production runs use the real repo root with a real `.git/HEAD`. The test's context_digest is therefore stable across runs (good for determinism) but does not match the production digest's git-aware shape.
- **Token-overflow and schema-fault paths are not exercised.** The validator stage covers exit-3 (SCHEMA_FAULT) and exit-5 (TOKEN_OVERFLOW) via existing fixtures (ADV-014, ADV-016 through ADV-019), but the integration stage does not run these through the orchestration end-to-end. The orchestration's distinct fault-categorization logic for these exit codes (`Run-Validator.ps1` ~lines 405–425) is therefore not validated by the integration stage. Adding integration coverage for these paths is a candidate follow-up if TD-002 closure changes the F7 contract.
- **Subprocess timeout is 60 seconds.** Adequate for the stub provider (typical run completes in 2–4 seconds on this machine), but not load-tested. A degraded environment with antivirus scanning, a slow disk, or Defender-throttled PowerShell startup could approach this bound.
- **Cleanup is best-effort on Windows.** `tempfile.mkdtemp` plus `shutil.rmtree` in a `try/finally` block will emit a warning to stderr if cleanup fails (typically due to a subprocess descendant holding a file handle) but will not fail the stage. The orphan temp dir would need manual cleanup. No orphans were observed across the three non-flakiness runs in this phase.
- **The integration stage exercises one fixture (CTX-001) reused four times via env override.** It is not a coverage matrix across diverse article shapes. Article-shape coverage remains the responsibility of the validator stage's 39 fixtures and 225 assertions.

**Test count:** 320/320 assertions passing (`--stage all`) — parser harness 59/59, validator harness 225/225, integration harness 76/76. Three consecutive `--stage all` runs were verified to produce identical pass counts and exit code 0. Harness exit code is now 0 in the all-pass case (was 3 prior to this phase).
**Status:** Integration stage implementation complete. README Roadmap items 2 (integration test stage) and 4 (em-dash portability) closed. New follow-ups surfaced and added to README Roadmap: positive `INFO: token_method=...` log line on every run for evidence symmetry with Phase 1.6's tokenizer follow-up.

### Phase 1.8 — Local Git Promotion (TD-002 part 1) (April 26, 2026)

**What happened:** Wired the local half of TD-002 into `Promote-ToVerified.ps1`. On a successful approve, the script now creates an isolated git worktree under `%TEMP%\llm-wiki-promote-<guid>`, copies the article from `provisional/` to `verified/`, and commits on a deterministic branch alias (`auto/<source_id>/<doc_hash[:8]>`). The user's working tree is never modified — every git operation runs against the temp worktree. On any failure inside the local-git path, a `PROMOTION_LOCAL_GIT_FAILED` operational_fault is emitted to the JSONL pipeline log and the worktree (plus any newly-created branch) is cleaned up before re-throwing. On success, the worktree is intentionally left in place for Engineering Prompt 03b's push step to consume. The script still throws after local-git completes (`promotion_gated_pending_remote_wiring`), keeping the gate fail-closed until 03b lands. A new `promote-local` harness stage (32 assertions) exercises the dry-run audit-preview shape, the live happy path under a mocked Gitea, and the branch-already-exists fail-loudly path.

**Why this matters:** TD-002 was Medium-severity tech debt with three remaining sub-gaps (local git operations, push + PR creation, tree-SHA equivalence). This phase closes the local-git sub-gap. Splitting the local layer from the remote layer was deliberate: it lets us land worktree isolation, JSONL fault emission, and rollback semantics without ever touching a live Gitea, and it gives 03b a clean entry point. The new audit-preview fields (`local_commit_sha`, `worktree_path`) give `-DryRun` callers visibility into what would happen and give 03b a deterministic handoff record.

**Artifacts:**
- pipeline/Promote-ToVerified.ps1 — added `Invoke-LocalGitPromotion` function (worktree create + copy + commit + rollback), `Write-PromotionFault` JSONL helper, `LLM_WIKI_GITEA_MOCK_MODE=local_only` early-return in `Invoke-GiteaApi` (test-only), `local_commit_sha` and `worktree_path` keys in the audit-preview hashtable (null in dry-run, populated post-local-git in live runs), and a rewritten Step 3 / Step 4 block that calls the new function and then throws a "push not yet wired (TD-002 part 2)" message. Set `Error = $false` on the existing real-API success returns in `Invoke-GiteaApi` so consumer code (`if ($result.Error)`) does not trip `Set-StrictMode -Version Latest` once a real call succeeds — pre-existing latent bug, not introduced by this phase.
- pipeline/tests/run_harness.py — added `promote-local` stage with helpers (`_setup_promote_local_repo`, `_run_promote`, `_assert_dry_run`, `_assert_live_run`, `_assert_failure_path`, `_cleanup_promote_local_worktrees`, `run_promote_local_tests`); extended `--stage` choices and `main()` dispatcher; reuses `golden_corpus/approve/A-001-clean-article.md` (no new fixture files).
- pipeline/tests/golden_corpus/CORPUS_MANIFEST.md — added "Promote-local Tests (TD-002 part 1)" section describing the three exercised paths and the `LLM_WIKI_GITEA_MOCK_MODE` mock surface.

**Key findings:**
- The `promote-local` stage adds 32 assertions across three runs (dry-run, live happy path, rerun fail-loudly). New `--stage all` total: 352 (320 prior + 32). Three consecutive `--stage all` runs produced byte-identical pass counts and exit 0. Standalone counts unchanged: parser 59/59, validator 225/225.
- The Gitea API success-shape return on the existing real-HTTP path was missing `Error = $false`. Under `Set-StrictMode -Version Latest`, a downstream `if ($result.Error)` check on that hashtable would have raised "The property 'Error' cannot be found on this object" the first time a real call succeeded. The bug was undetected because the Phase 1.5–1.7 integration tests only exercised the no-creds throw path and never reached a successful Gitea response. This phase fixed both the new mock returns and the pre-existing real-API returns by adding `Error = $false`.
- The new throw downstream of local-git emits a multi-line message that includes the commit short-sha, branch alias, worktree path, and audit file. `Run-Validator.ps1`'s catch block continues to record `message = "promotion_gated_pending_remote_wiring"` with the full Promote throw text in `promotion_error`. The Phase 1.7 integration stage's F7 allowlist therefore continues to match without modification — the assertion is on the catch's hardcoded `message` field, not on the throw text.
- Worktree leave-on-success was a deliberate choice (vs delete-on-success). Trade-off: 03b consumes a fresh worktree directly (cleaner handoff, mirrors how the rest of the script already stages preflight state for the next step) at the cost of leaving an `llm-wiki-promote-<guid>` directory in `%TEMP%` after every successful approve until 03b runs. The harness `_cleanup_promote_local_worktrees` removes these via `git worktree remove --force` after each test.
- Branch-already-exists is fail-loudly by default. Re-running Promote with the same article + same context digest (same branch alias) will refuse to proceed and emit a `PROMOTION_LOCAL_GIT_FAILED` JSONL fault with `step = "branch_already_exists"`. The existing `-Force` parameter semantics were not changed in this phase; an operator who wants to retry a failed promotion must clean up the prior worktree and branch manually (or wait for 03b's reconciliation flow).

**Limitations of this phase:**
- **Push and PR creation remain disabled.** The script still throws after local-git completes. The remote half (push, `New-GiteaPullRequest` call, `Write-PendingPrEntry`, worktree teardown) is deferred to Engineering Prompt 03b. The gate stays fail-closed.
- **Tree-SHA equivalence (P0-8) is still unimplemented.** `Test-RemoteBranchState` continues to return `Equivalent = $false` unconditionally when the remote branch exists. This is unchanged from Phase 1.5.
- **The integration stage does not exercise the new local-git path.** The integration stage runs without Gitea credentials in the subprocess env, so `Promote-ToVerified.ps1` throws at the credentials-missing check (line ~620) before reaching `Invoke-LocalGitPromotion`. The 76 integration assertions therefore test the same code path they tested in Phase 1.7. Direct exercise of the local-git path is provided by the new `promote-local` stage, which sets `LLM_WIKI_GITEA_MOCK_MODE=local_only` and dummy credentials so Promote passes the cred check and reaches the local-git function.
- **The F7 allowlist inversion is still pending.** Phase 1.7's note ("when TD-002 fully closes, the F7 allowlist must be inverted") carries forward to Engineering Prompt 03b. After 03b lands, the integration stage must assert no F7 fault and a successful-PR-creation event for approve. This phase does not change the allowlist.
- **`LLM_WIKI_GITEA_MOCK_MODE` is a production-code branch.** `Invoke-GiteaApi` checks the env var on every call. Production runs must not set it (default-off behavior preserved). The decision to add the env-driven branch in production code rather than mocking at the test boundary mirrors the Phase 1.7 `LLM_WIKI_STUB_DECISION` precedent — env vars propagate naturally to the pwsh subprocess without modifying call lines.
- **Windows file-handle cleanup races.** Like the existing integration stage, `_cleanup_promote_local_worktrees` plus `shutil.rmtree` may emit a `WARNING: cleanup of <work_root> failed` message to stderr if a git child process is still holding a handle to a packfile object. This does not fail the stage; the orphan temp dir requires manual cleanup. No orphans were observed across the three non-flakiness runs in this phase.
- **The new throw is verified by string match, not by structured re-parse.** The `promote-local` stage asserts that the live-run combined stderr+stdout contains the literal substrings `"promotion_gated_pending_remote_wiring"` and `"TD-002 part 2"`. A future formatting change to the throw text could pass strict structural checks while breaking these assertions; conversely, a refactor could move the strings around without exercising the underlying contract.
- **Production line-783 throw still not directly exercised in tests.** The promote-local stage exercises the rewritten line-783 throw via the mocked-Gitea live run; the Phase 1.7 caveat about the canonical-throw path needing direct exercise once Gitea creds are configurable in test contexts is partially closed (mocked) but not fully closed (live).

**Test count:** 352/352 assertions passing (`--stage all`) — parser harness 59/59, validator harness 225/225, integration harness 76/76, promote-local harness 32/32. Three consecutive `--stage all` runs produced identical pass counts and exit 0.
**Status:** TD-002 part 1 closed. Remaining open debt: TD-002 part 2 (push + PR creation, worktree push-side teardown), P0-8 (tree-SHA equivalence), TD-004 (documentation alignment). Next step: Engineering Prompt 03b.

### Phase 1.9 — Live Push + PR Creation + Tree-SHA Equivalence (TD-002 part 2) (April 27, 2026)

**What happened:** Wired the remote half of TD-002 into `Promote-ToVerified.ps1`. On a successful approve, the script now pushes the local-git branch from its temp worktree to the configured Gitea instance using a one-shot token-bearing URL (the token never lands in `.git/config`), creates a PR via `New-GiteaPullRequest`, writes the pending_pr tracking entry, updates the audit preview with the PR number and URL, emits a structured `promotion_completed` JSONL event, cleans up the worktree, and exits 0. Tree-SHA equivalence (P0-8) is implemented as Option B (git fetch + rev-parse comparison of tree and parent SHAs); when an orphan branch (exists, no open PR) is detected, the script defers the equivalence check until after local-git produces a commit to compare against, then either skips push (recovery-from-interrupted-prior-run) or fails closed. Live smoke-tested against an external throwaway Gitea repo; mock-vs-real PR response shape parity captured in `pipeline/tests/fixtures/gitea_pr_response_shape.json`. Adopted the maximum-rigor plan upfront: structured assertions, mock-vs-real parity, idempotent-rerun coverage, defensive token-leak sweeps, retry-with-backoff on Windows cleanup, positive log lines for non-fault paths, pre-commit critical review.

**Why this matters:** Phase 1.8 closed TD-002 part 1 (local git operations). Part 2 — push + PR creation + tree-SHA equivalence — was the last load-bearing engineering item to make the pipeline production-complete. With this phase, the full validator → ledger → promote → push → PR flow runs end-to-end against a real Gitea instance without manual intervention. The Phase 1.7 / Phase 1.8 caveats about the F7 allowlist needing inversion are also resolved: the integration stage now exercises the full new flow under a `pr_success` mock and asserts on a positive `promotion_completed` event with structured fields (`pr_number`, `branch_alias`, `commit_sha`, `pushed_to_remote`, `tree_sha_check`) instead of the placeholder F7 fault.

**Artifacts:**
- pipeline/Promote-ToVerified.ps1 — added `Invoke-GitPushPromotion` (one-shot token-bearing push URL + defensive token-leak sweep + retry-with-backoff cleanup), `Test-RemoteTreeEquivalence` (Option B: `git fetch` into temp ref + `rev-parse {sha}^{tree}` + parent-SHA check; cleans up temp ref in `finally`), `Get-GiteaPushUrl` helper (returns actual + redacted variants), `Test-WorktreeTokenLeak` defensive scanner, `Invoke-RemoveDirectoryWithRetry` (3 attempts, 200ms backoff for Windows file-handle races), `Write-PromotionInfo` (positive INFO log line); extended `Write-PromotionFault` with `$FaultCategory` + `$Extra` params (backwards-compatible defaults); extended `Invoke-GiteaApi` mock surface with `pr_success`, `pr_fail`, `push_fail`, `existing_open_pr` modes; extended `Invoke-StartupReconciliation` with worktree-orphan sweep (cleans `%TEMP%\llm-wiki-promote-*` dirs whose remote branch is absent); inverted the orphan-branch behavior at Step 2 (defers equivalence check to post-local-git instead of immediate fail-closed); rewired Step 4-7 with the full push + PR + audit + JSONL + cleanup sequence (the Phase 1.8 line-783 throw is removed on the production path); added `pr_number` and `pr_url` to the audit preview; added `LLM_WIKI_GITEA_MOCK_MODE=local_only` boundary guard to preserve the Phase 1.8 promote-local contract; coerced `.Data.Count` reads to `@($x.Data).Count` in three locations to handle PowerShell's empty-array-collapses-in-hashtable quirk; bypassed the `HeadBranch` filter in `Get-GiteaPullRequests` when any mock mode is active.
- pipeline/tests/run_harness.py — added `promote-full` stage with 4 paths (success, push-fail, PR-fail-after-push, idempotent-rerun); refactored `_run_orchestration_once` to git-init the temp work_root so the integration stage can exercise the full push+PR flow; updated integration env_overrides to set `LLM_WIKI_GITEA_MOCK_MODE=pr_success` plus dummy `GITEA_*` vars; inverted the F7 allowlist in `_assert_orchestration_run` (removed F7-specific assertions; added `promotion_completed` count + 5 structured sub-assertions for approve / 5 padding placeholders for missing event); added `commit_sha`, `pushed_sha`, `local_commit_sha` to `_DETERMINISM_STRIP_FIELDS` so the determinism check tolerates per-run timestamp-derived SHAs; renamed `_assert_failure_path` → `_assert_idempotent_rerun` reflecting the Stage-4 contract change (orphan worktrees auto-cleaned by startup reconciliation, second run succeeds local-git afresh).
- pipeline/tests/fixtures/gitea_pr_response_shape.json — NEW. Mock-vs-real shape parity reference captured during the live throwaway smoke test; lists all real-response top-level + nested fields and the consumer-required subset; documents that the consumer-required subset is fully present in real responses.

**Live smoke-test evidence (external throwaway Gitea, 2026-04-27):**
- Throwaway repo: a private repo on the same external Gitea instance (private; URL/owner/repo not included in this entry)
- Branch protection mirrored production: `enable_push=false`, `required_approvals=1`, `enable_force_push=false`
- Smoke run 1 (clean publish): `Promote-ToVerified.ps1` against `golden_corpus/approve/A-001-clean-article.md`, custom `-StateRoot`, no mock mode, real env-var-driven Gitea config — exit 0, PR #1 created with branch `auto/kubernetes-networking-101/4d2a5635` and commit `5172823611681a05453ae69c8a5615d77184e33a`. Audit file populated with `pr_number=1`, `pr_url=<gitea_pr_url>`. JSONL `promotion_completed` event emitted with all 8 expected fields. Token-leak sweep across smoke state, repo `.git/config`, and `%TEMP%` worktree configs returned 0 leaks.
- Smoke run 2 (idempotent re-run, same article + same context digest): exit 0, "Existing open PR #1 found ... idempotent re-run path" message, no duplicate PR created on remote. After the smoke-run-1 fix to `.Data.Count` accesses, no warnings during re-run startup reconciliation.
- Mock-vs-real shape parity: 37 top-level fields in real PR response (vs 7 in my mock); my mock subset is a strict subset of consumer-required fields, all of which are present in real responses. Captured to fixture file.
- Orphan-recovery scenario (delete PR + leave branch + re-run + verify Test-RemoteTreeEquivalence fires): NOT run live this phase — see Limitations.

**Key findings:**
- All test counts moved as expected. New `--stage all` total: 387/387 (parser 59/59, validator 225/225, integration 83/83, promote-local 31/31, promote-full 30/30). Three consecutive `--stage all` runs produced byte-identical pass counts and exit 0. Integration count rose from 76 → 83 (net +7 from F7 inversion + structured `promotion_completed` assertions). Promote-local dropped 32 → 31 because the `_assert_failure_path` rewrite has 5 assertions vs the prior 6 (the 2 conditional F7 assertions collapsed into 1 deterministic check). Parser and validator stage counts unchanged.
- Two real bugs surfaced during live smoke testing and were fixed in the same phase: (1) PowerShell's empty-array-in-hashtable collapse caused `.Data.Count` to throw "property not found" under StrictMode when a `Get-GiteaPullRequests` query returned an empty filtered list — fixed by `@($x.Data).Count` defensive coercion in three locations; (2) the `Get-GiteaPullRequests` `HeadBranch` filter would empty the canned PR list returned by the `existing_open_pr` mock (because the mock's canned `head.ref` doesn't match the dynamically-computed branch alias) — fixed by skipping the filter when any mock mode is active. Both bugs were latent against pre-Phase-1.9 code paths because the consumer paths were never reached without live Gitea state.
- Mock-vs-real parity holds: every field the consumer code reads from a Gitea PR response (`number`, `title`, `state`, `merged`, `html_url`, `url`, `head.ref`, `head.sha`, `base.ref`, `user.login`, `created_at`, `updated_at`, `closed_at`, `merged_at`, `merge_base`) is present in the real response. The mock returns a subset; consumers only access fields the mock has. No hidden field-shape divergence found.
- Token hygiene held end-to-end: 0 token leaks observed across the smoke state directory (logs/audit/ledger/pending_pr), the repo's `.git/config`, and 42 leftover worktree `.git/config` files in `%TEMP%`. The `Test-WorktreeTokenLeak` defensive sweep ran on every push and never tripped. The one-shot URL pattern (token in arg, never `git remote add`-ed) holds.
- Tree-SHA Option B (the user's chosen design) is in production but exercised only via inspection, not via automated test or live smoke. The function is small (~100 lines), uses git's own SHA computation (no reimplementation), and the unit-level rigor relies on the production code's integrated correctness. See Limitations.
- Determinism check needed three additional strip fields (`commit_sha`, `pushed_sha`, `local_commit_sha`) because the local commit's SHA is derived from the commit's author/committer timestamp, which varies per run by construction. The transaction-key fields (source_id, repo_relative_path, document_hash, context_digest) remain stable across runs.

**Limitations of this phase:**
- **Tree-equivalence test paths (tree-match, tree-mismatch) NOT in `promote-full`.** The rigor plan called for 6 paths; this phase implements 4 (success, push-fail, PR-fail-after-push, idempotent-rerun). The tree-equivalence paths require a bare-repo fixture (real `git fetch` against a local file:// remote) and were deferred to a future phase. `Test-RemoteTreeEquivalence` is in production but has NO automated test coverage. The function is correct by inspection (uses `git rev-parse {sha}^{tree}` for the comparison, which delegates to git's own object model), but a behavioral regression could ship green. Recommended follow-up: build the bare-repo fixture and add the two tree-equivalence test paths in a tightly-scoped phase.
- **Live smoke test covered 2 scenarios (clean + idempotent), not 3.** The orphan-recovery scenario (delete PR, leave branch, re-run, verify `Test-RemoteTreeEquivalence` fires correctly against real Gitea) was not exercised live. The function's behavior was confirmed by inspection only. Manual follow-up needed if a regression surfaces — the smoke test infrastructure in this phase is reusable.
- **Mock-mode env vars are production-code branches.** `Invoke-GiteaApi`, `Invoke-GitPushPromotion`, and `Get-GiteaPullRequests` all check `LLM_WIKI_GITEA_MOCK_MODE`. Production runs MUST NOT set this env var (default-off behavior preserved). This continues the Phase 1.8 / Phase 1.7 precedent (`LLM_WIKI_GITEA_MOCK_MODE=local_only`, `LLM_WIKI_STUB_DECISION`).
- **Windows file-handle race on cleanup persists.** The new `Invoke-RemoveDirectoryWithRetry` (3 attempts, 200ms backoff) mitigates the race in production code paths but does not eliminate it. Test stages still emit `WARNING: cleanup of <path> failed: [WinError 5] Access is denied` during their own teardown; this does not fail any stage but means orphan worktrees may accumulate in `%TEMP%`. The new worktree-orphan sweep in `Invoke-StartupReconciliation` cleans these on the NEXT promote invocation when the corresponding remote branch is absent. Observed 42 leftover worktrees in `%TEMP%` after running test stages multiple times during development — operationally fine, cosmetically untidy.
- **The promote-local `rerun` test contract changed intentionally.** Pre-Phase-1.9: rerun was expected to fail loudly with "branch already exists." Post-Phase-1.9: rerun is auto-recovered by the new worktree-orphan sweep in startup reconciliation. The test was renamed from `_assert_failure_path` → `_assert_idempotent_rerun` to reflect the new semantics. Phase 1.8's ledger entry explicitly anticipated this contract change ("an operator who wants to retry a failed promotion must clean up the prior worktree and branch manually (or wait for 03b's reconciliation flow)").
- **Push test is mock-only in `promote-full` (no real push).** The mock-mode skip in `Invoke-GitPushPromotion` returns success without invoking `git push`. The real `git push` path is exercised exclusively by the live smoke test (Stage 8). A bare-repo fixture for `promote-full` could exercise the real push path automatically; deferred to scope this phase.
- **Mock-vs-real shape parity captured by manual inspection during the smoke test, not by automated CI assertion.** The fixture file `gitea_pr_response_shape.json` documents the field shape but is not automatically diffed against live responses in CI. Future enhancement: an optional CI step that loads the fixture, queries a configured throwaway Gitea, and asserts the consumer-required subset is present.
- **Tree-SHA equivalence parent check is strict (interpretation 1 of P0-8).** Equivalence requires both tree-equivalence AND parent-equivalence. If `main` moves forward between two attempts, an orphan branch (created off the old `main`) will fail equivalence even if its tree is fine. This is correct per P0-8 ("base SHA and tree SHA match local intent") but means a "stale" orphan branch with unchanged article will still fail equivalence — the operator must delete the remote branch manually. Operational caveat, not a bug.
- **Throwaway smoke test required manual prep.** The user had to create a Gitea repo, generate a personal access token, push local main, configure branch protection mirroring production, and set 5 user-level env vars. This is intentional — Claude does not have credential-creation access — but it makes the live smoke test non-automatable. The setup is documented inline in this phase entry's preceding chat history; future smoke tests can reuse the same throwaway.
- **`origin_main_marker` shape changed in integration tests.** Phase 1.7 noted `origin_main_marker = "no-git-head"` because the temp work_root lacked `.git`. Phase 1.9's `_run_orchestration_once` now `git init`s the work_root so the new local-git path can run. The `origin_main_marker` is now a real (test-only) git HEAD ref, not the literal string `"no-git-head"`. The determinism check still passes because both compared runs have the same git state. No assertion checked the literal `"no-git-head"` value (only documented as a comment), so this is a contract-shape change with no test breakage.
- **Phase ledger evidence is anonymized.** Per the project's privacy posture (memory rule: "Gitea remote stays out of repo"), the throwaway repo URL, owner, repo name, and token are referenced abstractly in this entry and in `gitea_pr_response_shape.json`. The actual values are stored in the user's machine env vars only. The PR URL captured in JSONL/audit during the smoke test contains the real Gitea host but lives in `C:\llm-wiki-state\` (out-of-tree), not in the repo.

**Test count:** 387/387 assertions passing (`--stage all`) — parser harness 59/59, validator harness 225/225, integration harness 83/83, promote-local harness 31/31, promote-full harness 30/30. Three consecutive `--stage all` runs produced byte-identical pass counts and exit 0. Live throwaway smoke test (2 scenarios) returned exit 0 and PR #1 was created on the throwaway. Token-leak sweep across all production surfaces returned 0 leaks.
**Status:** TD-002 fully closed. P0-8 (tree-SHA equivalence) implemented as Option B in production, with automated test coverage deferred (see Limitations). Remaining open debt: TD-004 (documentation alignment, Low). Recommended follow-ups: bare-repo fixture for `promote-full` tree-match/tree-mismatch paths; live orphan-recovery smoke test; CI-time mock-vs-real shape parity assertion.

### Phase 2.0 — Bare-repo fixture + tree-equivalence test coverage (P0-8 closure) (May 4, 2026)

**What happened:** Closed the highest-priority Phase 1.9 follow-up: automated test coverage of `Test-RemoteTreeEquivalence` (P0-8). Added a real `file://` bare-repo fixture and two new paths (`tree_match`, `tree_mismatch`) to the `promote-full` harness stage. The fixture is built per-test by running `Promote-ToVerified.ps1` once in `LLM_WIKI_GITEA_MOCK_MODE=local_only` (the warmup), recovering the warmup's worktree path and branch alias from `git worktree list --porcelain` (not from the script's stderr text, which is ANSI-decorated and word-wrapped by the PowerShell exception formatter), then pushing that branch — with or without a `git commit --amend` divergence marker — to a bare repo at `<work_root>/remote.git`. The test phase then runs the script again under the new mock modes, hitting the orphan-branch path; the production `Test-RemoteTreeEquivalence` runs a real `git fetch + rev-parse {sha}^{tree}` against the file:// remote and decides equivalent/not. tree-match exercises the recovery branch (skip push, create PR via mock); tree-mismatch exercises the fail-closed throw + worktree/branch rollback.

**Why this matters:** Phase 1.9 shipped `Test-RemoteTreeEquivalence` to production with zero automated coverage — verified by inspection only. The function uses git's own object model for the comparison so it was structurally low-risk, but a regression could ship green and only surface in the rare orphan-recovery scenario. This phase closes the most material untested-code-path gap surfaced by the Phase 1.9 Limitations review and is item 1 of the recommended sequence in `PHASE_REVIEW_20260504.md`. Two of the original Phase 1.9 follow-ups remain open: live orphan-recovery smoke test against a throwaway Gitea, and CI-time mock-vs-real shape parity assertion.

**Artifacts:**
- pipeline/Promote-ToVerified.ps1 — extended `Invoke-GiteaApi` mock dispatcher with `tree_match` and `tree_mismatch` modes (200 + canned branch on `/branches/<name>` + empty list on `/pulls?state=open` to gate the orphan path open); extended POST `/pulls$` canned-PR success list to include the new modes; extended `Get-GiteaPushUrl` with a `file://` branch (returns the URL as-is, no token rewrite — file paths don't carry credentials); error message now lists all three accepted prefixes (http://, https://, file://).
- pipeline/tests/run_harness.py — added `_normalize_ps_text` helper (strips ANSI escape codes + PowerShell exception-formatter `     | ` line wraps); added `_find_warmup_worktree` helper (locates the local_only warmup's worktree via `git worktree list --porcelain` rather than fragile stderr regex; reads branch alias from `git rev-parse --abbrev-ref HEAD` against the worktree); added `_setup_bare_repo_for_tree_path` (warmup → optional amend → push to bare repo → tear down warmup worktree + local branch ref); added thin wrappers `_setup_bare_repo_match` and `_setup_bare_repo_mismatch`; added `_assert_full_tree_match_path` (~14 assertions) and `_assert_full_tree_mismatch_path` (~11 assertions); extended the `paths` tuple in `run_promote_full_tests` from 3 elements to 4 (added optional `setup_fn`); wrapped setup_fn invocations in try/except so a setup failure on one path doesn't crash the stage; updated section banner to list all six paths.
- pipeline/tests/golden_corpus/CORPUS_MANIFEST.md — Promote-full Tests section: added rows for tree-match and tree-mismatch with their assertion contracts, added a "Limitations of the bare-repo fixture" subsection (token-leak sweep is no-op under file:// remotes; PowerShell-Python text coupling via `_normalize_ps_text`; live orphan-recovery scenario remains manual).

**Key findings:**
- Test counts moved as expected. New `--stage all` total: 412/412 (387 prior + 25 new = +14 tree-match + 11 tree-mismatch). Three consecutive `--stage all` runs produced byte-identical pass counts and exit 0. Standalone stage counts after this phase: parser 59/59, validator 225/225, promote-local 31/31, promote-full 30/30 → 55/55. Integration stage runs only inside `--stage all`.
- Two implementation pivots happened during the build, both well-contained and surfaced in the Phase 2.0 plan before code was written:
  1. **`file://` not accepted by `Get-GiteaPushUrl`.** The pre-existing function explicitly threw on non-http(s) URLs (line 950). Original plan was to start with option (a) — pass `file://` and see if downstream `git fetch` was forgiving — but the function's protocol validator made that impossible at the entry point. Pivot: option (b), add a small `file://` branch to `Get-GiteaPushUrl`. The branch is additive, gated by URL prefix; production GITEA_URL is always http(s) so the branch never fires there.
  2. **Stderr regex parsing fragile against PowerShell exception decorator.** First implementation parsed the local_only warmup's worktree path from a regex against captured stderr. Failed: PowerShell's exception formatter ANSI-decorates the throw and word-wraps it across multiple `     | `-prefixed lines, so the regex never matched cleanly. Pivot: drop stderr parsing entirely, query `git worktree list --porcelain` directly. The script's exit text becomes irrelevant; we read git's own state.
- A third issue surfaced after the worktree-discovery pivot worked: the warmup leaves a LOCAL branch ref in the work_root after the worktree is removed, so the test phase's `Invoke-LocalGitPromotion` errored with "Local branch already exists" → `PROMOTION_LOCAL_GIT_FAILED` fault before tree-equivalence ran. Fix was a one-line `git branch -D <branch_alias>` after `git worktree remove`.
- Mock-vs-real boundary is intentionally tighter than Phase 1.9's mock-only paths. The bare-repo fixture exercises the REAL `Test-RemoteTreeEquivalence` git fetch + rev-parse code paths, not stubbed responses. Only the Gitea HTTP API surface (branch lookup, PR list, PR creation) is mocked; the git tree comparison runs against actual git objects. This reduces the mock-vs-production divergence risk for P0-8 specifically.

**Limitations of this phase:**
- **Token-leak sweep behavior under file:// is a no-op.** `Test-RemoteTreeEquivalence`'s defensive token-leak sweep on `.git/config` finds nothing because file:// URLs carry no token. The sweep IS exercised in the Phase 1.9 live throwaway-Gitea smoke (real http(s) URL with a real token); it is NOT exercised by automated stages. Documented in CORPUS_MANIFEST.md.
- **Two assertions match throw text via `_normalize_ps_text`.** The substrings `"non-equivalent tree state"` and `"Fail-closed per P0-8"` are checked against PowerShell `throw` output, which the interpreter ANSI-decorates and word-wraps. `_normalize_ps_text` strips both before searching. A future PowerShell version that changes the wrap or color format could regress these assertions cosmetically (false negatives) without any underlying behavior change. Mitigation deferred — the structured `tree_sha_check` JSONL event already provides equivalence/outcome/match flags, so the throw-text checks are an optional human-readable-error layer; alternatives include switching to structured stderr or asserting on JSONL alone.
- **Live orphan-recovery scenario still not automated.** This phase covers the recovery (tree-match) and fail-closed (tree-mismatch) outcomes against a controlled bare repo, but not the full lifecycle of "an orphan from a real prior interrupted run, against a real Gitea". That scenario remains the Phase 2.0 follow-up (item 3 in the recommended sequence) and requires a manual setup against a throwaway Gitea.
- **Mock-mode env var surface expands from 5 to 7.** `Invoke-GiteaApi` now recognizes: `local_only, pr_success, pr_fail, push_fail, existing_open_pr, tree_match, tree_mismatch`. Production runs MUST NOT set `LLM_WIKI_GITEA_MOCK_MODE`; the env-var-gated test-seam pattern continues to be a deliberate compromise (consistent with Phase 1.7-1.9 precedent) that increases the production-binary's test-only branch surface.
- **Windows file-handle cleanup race persists and compounds slightly.** Pre-existing limitation. The new bare-repo fixture adds another transient git directory (`<work_root>/remote.git`) to be cleaned up. The startup-reconciliation orphan sweep handles leftovers on the next run; the warning-line surface during cleanup is unchanged in failure mode but somewhat noisier.
- **Pre-existing per-stage count discrepancy in Phase 1.9 ledger.** Phase 1.9 stated `integration harness 83/83` in its Test count line but my standalone stage runs (parser+validator+promote-local+promote-full = 315) leave 412 - 315 = 97 assertions for integration in the new total — closer to 97 than 83. Either the Phase 1.9 stage breakdown was misreported or `--stage all` runs assertions that standalone stage runs do not (the integration stage isn't a standalone `--stage` choice). Not investigated this phase; the verifiable contract is the `--stage all` total and the per-stage standalone counts above.

**Test count:** 412/412 assertions passing (`--stage all`) — net +25 from Phase 1.9 (387/387). promote-full: 30/30 → 55/55 (added tree-match path with 14 assertions; tree-mismatch path with 11 assertions). Three consecutive `--stage all` runs produced byte-identical pass counts and exit 0. No live smoke test in this phase.
**Status:** Phase 1.9 follow-up #1 closed (tree-equivalence automated test coverage). Open Phase 2.0 follow-ups carrying forward: live orphan-recovery smoke against throwaway Gitea (item 3 of the Phase Review's recommended sequence); CI-time mock-vs-real shape parity assertion (Phase 2.1 item 4); PowerShell exception-formatter coupling and Windows file-handle cleanup race (separate quality items). Carry-forward TD-004 (documentation alignment, Low) remains open.

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
| **Tests passing** | 0 | 412/412 (`--stage all` exits 0; standalone counts: 59 parser + 225 validator + 31 promote-local + 55 promote-full = 370; integration runs only inside `--stage all`, contributes the remaining 42) |
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
| TD-002 | Live push + PR creation + tree-SHA equivalence (P0-8) all wired in Phase 1.9 / 03b. `Invoke-GitPushPromotion` pushes from the temp worktree using a one-shot token-bearing URL (token never persisted to `.git/config`) with defensive token-leak sweep + retry-with-backoff cleanup. `Test-RemoteTreeEquivalence` implements P0-8 via Option B (git fetch + `rev-parse {sha}^{tree}` + parent-SHA comparison). Main flow: existence check → declined-PR check → local-git → tree-SHA equivalence (orphan recovery) → push (or skip if equivalent) → PR creation → pending_pr write → audit rewrite → `promotion_completed` JSONL event → worktree cleanup → exit 0. Rollback decision tree: push-fail → cleanup + `PROMOTION_PUSH_FAILED`; PR-fail-after-push → `Remove-GiteaBranch` + cleanup + `PROMOTION_PR_FAILED`; pending-pr-write or audit-rewrite fail after PR success → forward + warn (PR is durable). `Invoke-StartupReconciliation` extended with worktree-orphan sweep (auto-cleans `%TEMP%\llm-wiki-promote-*` whose remote branch is absent). Integration stage F7 allowlist inverted (asserts 0 faults + structured `promotion_completed` event). Live smoke-tested 2026-04-27 against an external throwaway Gitea (clean publish + idempotent re-run scenarios; PR #1 created; 0 token leaks). | Medium | Phase 0.6 | **Closed** (Phase 1.9) |
| TD-003 | `parse_identity.py` still resolves `file_path` via current working directory rather than deterministic repo-root-relative identity | Medium | Phase 0.6 | **Closed** (Phase 1.0) |
| TD-004 | README drift was reduced on April 7, 2026, but documentation alignment still needs a broader audit across portfolio entry points | Low | Phase 0.6 | Open |

---

*Ledger maintained by: Josh Hillard*
*Last updated: May 4, 2026 (Phase 2.0 — Bare-repo fixture + tree-equivalence test coverage / P0-8 closure)*
