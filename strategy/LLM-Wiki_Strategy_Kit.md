# LLM-Wiki Content Pipeline — Strategy Kit

**Rev 3.4 — April 6, 2026**


**LLM-WIKI CONTENT PIPELINE**
Strategy Kit

PRD  |  ADR  |  Roadmap  |  Code Review  |  FMEA  |  LLM Infrastructure
Prepared for: Cross-Functional Review (Engineering + Product)
Owner: Josh Hillard  |  April 2026
**Status: Design Complete — Implementation Ready**
*Portfolio Context: Complements Céal (Career Signal Engine — async ETL pipeline for job listings), Moss Lane (Trading Infrastructure), and Career Campaigns*


## Part 1: Product Requirements Document

*LLM-Driven Content Validation & Promotion Pipeline for Wiki Repositories*


### Problem Statement

Organizations maintaining wiki-style knowledge repositories face a fundamental quality control problem: content enters the corpus without structured validation, creating an ungoverned knowledge substrate where inaccurate, outdated, or policy-violating articles accumulate silently. Manual review does not scale, and existing CI/CD tooling is not designed for natural-language content evaluation.
Without an automated validation pipeline, the cost is threefold: content quality degrades over time, subject-matter experts burn cycles on manual review that could be automated, and there is no auditable trail connecting a published article to the evaluation criteria it satisfied. This gap is especially acute for teams using LLMs to generate or assist draft content, where the volume of new material outpaces human review capacity.

### Goals

- Automated policy enforcement: Every draft article is evaluated against a versioned policy bundle before it can enter the verified corpus. Target: 100% of promotions gated by LLM validation within 30 days of deployment.
- Deterministic auditability: Every promotion decision is traceable via a transaction key linking the source file, policy version, evaluation result, and PR. Target: Any article in verified/ can be traced to its validation record in under 60 seconds.
- Self-invalidating cache: When pipeline logic, policy rules, or the upstream repo state changes, previously-approved evaluations are automatically invalidated and articles re-enter the queue. Target: Zero stale approvals persist after a policy or code change.
- Idempotent retries: Any interrupted or failed promotion can be safely retried without creating duplicate branches, duplicate PRs, or corrupted Git state. Target: 100% clean workspace after any failure mode.
- Reduced SME review burden: Shift subject-matter expert time from first-pass review to exception handling. Target: 60% reduction in manual review hours within 90 days.

### Non-Goals

- Real-time editing integration: The pipeline operates on committed drafts in provisional/, not on live editor sessions. Interactive co-authoring is a separate initiative.
- Multi-model consensus: V1 supports hybrid deployment (managed API + self-hosted), but ensemble validation requiring agreement across multiple models is deferred. Each evaluation uses one model path per transaction.
- Content generation: This pipeline validates and promotes content. It does not generate articles. Content creation tooling is out of scope.
- Cross-platform portability: V1 targets Windows (PowerShell 5+) with Gitea. Linux/GitHub/GitLab support is a future consideration.
- Model fine-tuning or alignment in v1: LoRA/QLoRA and DPO are LATER-phase capabilities. However, the ledger retains full structured evaluation payloads from day one to serve as future training data.

### User Stories


#### Wiki Maintainer

- As a wiki maintainer, I want draft articles to be automatically evaluated against our content policy so that I only review articles the system flags as exceptions.
- As a wiki maintainer, I want approved articles to be promoted via pull request so that I retain final merge authority without doing first-pass review.
- As a wiki maintainer, I want to see a clear audit trail for every promoted article so that I can defend content decisions during compliance reviews.

#### Content Author

- As a content author, I want my draft to be evaluated automatically after I commit it to provisional/ so that I get structured feedback without waiting for a human reviewer.
- As a content author, I want rejected drafts to include specific reasons so that I can revise and resubmit efficiently.

#### Operations / CI Owner

- As a CI owner, I want the pipeline to be fully idempotent so that I can safely re-run it after any interruption without manual cleanup.
- As a CI owner, I want all pipeline state stored outside the Git repo so that the automation clone stays pristine and rebasing never conflicts with pipeline metadata.

### Requirements


#### Must-Have (P0)


| # | Requirement | Component | Acceptance Criteria | Reference |
| --- | --- | --- | --- | --- |
| P0-1 | Single-parser identity extraction via parse_identity.py | parse_identity.py | No other component parses frontmatter; all identity flows through one parser | LLM_WIKI_CONTROL_PLANE_REVIEW.md § Critical Invariant 1 |
| P0-2 | Composite context digest (control-plane + model-config hash) | Run-Validator.ps1 | SHA256 of pipeline scripts, policy bundle, schema, origin/main SHA, and validator_config.json; any change produces a new digest | LLM Content Pipeline Hardening.md § 1 |
| P0-3 | Canonical transaction key: source_id + path + doc_hash + context_digest | All components | Identical key used in ledger, branch name, PR metadata, and audit logs | LLM_WIKI_CONTROL_PLANE_REVIEW.md § Transaction Identity |
| P0-4 | LLM output validated against validation_result.schema.json | validator_runner.py | Schema-invalid LLM output triggers system_fault, never reaches promotion | LLM_WIKI_CONTROL_PLANE_REVIEW.md § validator_runner.py |
| P0-5 | PR-based promotion with namespace preservation | Promote-ToVerified.ps1 | provisional/a/b.md promotes to verified/a/b.md; never flattened | LLM_WIKI_CONTROL_PLANE_REVIEW.md § Critical Invariant 5 |
| P0-6 | External state storage (ledger + audit logs outside repo) | Run-Validator.ps1, Promote-ToVerified.ps1 | No pipeline metadata committed to the wiki repo | LLM_WIKI_CONTROL_PLANE_REVIEW.md § Critical Invariant 3 |
| P0-7 | Idempotent promotion with full workspace rollback | Promote-ToVerified.ps1 | Retry after interruption produces zero orphaned branches, zero duplicate PRs | LLM Content Pipeline Hardening.md § 3 |
| P0-8 | Tree SHA equivalence for remote PR verification | Promote-ToVerified.ps1 | Remote PR accepted as equivalent only when base SHA + tree SHA match local intent | LLM Content Pipeline Hardening.md § 3 |
| P0-9 | Model configuration manifest (ops/validator_config.json) included in context digest | Run-Validator.ps1 | Changing any digest-contributing manifest field (provider, model_id, quantization_level, temperature, top_p, max_context_tokens, system_instruction_hash, lora_adapter_path) rotates the digest and invalidates cached evaluations. tokenizer_id is present in the manifest for budget calculation but excluded from the digest (derived from model_id). | Cross-functional review amendment, April 2026 |
| P0-10 | Frontmatter enforcement layer in parse_identity.py (regex + length limits) | parse_identity.py | source_id must match restricted identifier format ^[a-zA-Z0-9-]{1,36}$; all values capped at 256 bytes; violations return structured error JSON | Strategy Kit Part 4 § S3 + cross-functional review |
| P0-11 | Declined PR lifecycle handling in Promote-ToVerified.ps1 | Promote-ToVerified.ps1 | Declined PRs detected by querying Gitea API for state=closed AND merged=false on the transaction key’s branch; file routed to declined_by_human ledger state | Cross-functional review amendment, April 2026 |
| P0-12 | Token budget enforcement with TOKEN_OVERFLOW exit code | validator_runner.py | Pre-send token count check; policy_bundle + article must fit within model context window; overflow triggers EXIT_TOKEN_OVERFLOW (code 5) and file skips evaluation | Part 7 § NOW: Validation Runtime Contract |
| P0-13 | Runtime parity harness: managed vs. self-hosted agreement testing | Test harness | Golden corpus evaluated by both model paths; decision agreement rate meets defined threshold before self-hosted leg activates for production | Part 7 § NOW: Validation Runtime Contract |
| P0-14 | Ledger retains full structured evaluation payloads (not just approve/reject) | Run-Validator.ps1, validator_runner.py | Each ledger entry stores: full model output, model config, reviewer outcome (when available), transaction identity — sufficient for future DPO training | Part 7 § LATER: Model Adaptation (log now, build later) |


#### Nice-to-Have (P1)


| # | Requirement | Rationale |
| --- | --- | --- |
| P1-1 | Structured rejection feedback written back to a sidecar file alongside the draft | Closes the loop for content authors without requiring them to read the ledger |
| P1-2 | Dashboard or report view of pipeline throughput, rejection rates, and evaluation latency | Operational visibility for CI owners and product stakeholders |
| P1-3 | Configurable escalation routing (e.g., certain policy violations auto-assign a reviewer) | Reduces time-to-resolution for escalated content |


#### Future Considerations (P2)


| # | Requirement | Design Implication |
| --- | --- | --- |
| P2-1 | Vertex AI regime classification integration for validator_runner.py | Runner should accept model config as an external parameter, not hardcode provider |
| P2-2 | Multi-model consensus (ensemble validation with agreement threshold) | Schema should support multiple evaluation records per transaction key |
| P2-3 | Linux / GitHub / GitLab portability | Avoid Windows-specific APIs in Python components; isolate PowerShell to orchestration layer |


### Success Metrics


#### Leading Indicators (Days to Weeks)


| Metric | Target | Measurement |
| --- | --- | --- |
| Validation coverage | 100% of provisional/ files evaluated within 24h of commit | Ledger entry count vs. provisional/ file count |
| Idempotency | Zero orphaned branches or duplicate PRs after 50 consecutive retry tests | Automated test suite |
| Cache invalidation | 100% re-evaluation after any context digest change | Modify policy bundle, verify all pending files re-enter queue |
| Pipeline latency | Median draft-to-PR time under 5 minutes | Timestamp delta: ledger entry creation to PR creation |


#### Lagging Indicators (Weeks to Months)


| Metric | Target | Measurement |
| --- | --- | --- |
| SME review hours | 60% reduction within 90 days of deployment | Before/after time tracking comparison |
| Content quality | Fewer than 5% of auto-promoted articles require post-merge correction | Post-promotion revert or edit rate in verified/ |
| Pipeline reliability | 99%+ successful completion rate per run (excluding expected rejections) | system_fault count / total evaluations |


### Open Questions


| # | Question | Owner | Blocking? |
| --- | --- | --- | --- |
| 1 | Which managed API provider is the primary evaluation path for v1, and which self-hosted model/serving stack is the parity candidate? | Engineering + Product | **Resolved (Phase 1.3):** Anthropic Claude Sonnet 4.6 selected as initial managed-API primary (ADR-004). Self-hosted parity candidate deferred per ADR-002 until managed path is operational. |
| 2 | What is the Gitea branch protection configuration? (affects promotion script behavior) | Engineering / Infra | **Resolved (Phase 1.5):** External Gitea instance configured (private, not included in this repository). Branch protection on main: `enable_push=false`, `required_approvals=1`, `enable_force_push=false`. Gitea credential flow validated locally; credentials are not stored in this repository. Verified live via API on April 9, 2026. |
| 3 | Should rejected articles receive structured feedback as a sidecar file or only in the ledger? | Product | No — P1 scope, can resolve during implementation |
| 4 | Rate limit and cost guardrails for the LLM evaluation step? | Engineering | No — can add semaphore after core flow works |


## Part 2: Architecture Decision Record

*ADR-001: Trust-Nothing Control Plane for LLM Content Promotion*

**Status:** Proposed
**Date:** April 2026
**Deciders:** Josh Hillard (Owner), Engineering review, Product stakeholder sign-off

### Context

We need a system to validate wiki content produced or assisted by LLMs before it enters the verified corpus. The core tension is between automation speed and content governance: we want the throughput benefits of LLM-assisted content but cannot allow ungoverned promotion to the canonical knowledge base.
The environment imposes several constraints: Windows-first (PowerShell 5+), Gitea-hosted Git, branch-protection on main, and a requirement that all pipeline state live outside the repository so the automation clone remains pristine for rebasing and concurrent runs.
*A critical architectural choice emerged during cross-functional review: the validation model deployment cannot be single-provider. The pipeline requires a hybrid deployment model — managed API (Vertex AI / OpenAI / Anthropic) for primary evaluation, with a self-hosted open model (Llama, Mistral) for specialized or cost-sensitive tasks such as regime classification. This hybrid posture introduces new requirements around token budgeting (different tokenizers per model), runtime parity testing (managed and self-hosted must produce compatible decisions), and model configuration as a first-class input to the context digest.*

### Decision

Adopt a four-component control plane with deterministic transaction identity, composite context digests, PR-gated promotion, and externalized state. The architecture treats LLM output as untrusted at every boundary and enforces five critical invariants documented in LLM_WIKI_CONTROL_PLANE_REVIEW.md.
The validation runtime uses a hybrid deployment model: managed API as the primary evaluation path, self-hosted model as a secondary path gated by a runtime parity harness. Both paths share the same exit code contract, schema validation, and ledger integration. The model path (managed vs. self-hosted) is recorded in the transaction identity via validator_config.json and included in the context digest, ensuring that switching model paths invalidates cached evaluations.
*The context digest is expanded from a file-based list to a System Configuration Manifest. ops/validator_config.json captures provider, model_id, quantization_level, temperature, top_p, max_context_tokens, system_instruction_hash, lora_adapter_path (null for managed API), and tokenizer_id. All fields except tokenizer_id (derived from model_id) are included in the SHA256 concatenation so that model drift, provider changes, or inference configuration changes invalidate previous evaluation states.*

### Options Considered


#### Option A: Trust-Nothing Control Plane (Selected)


| Dimension | Assessment |
| --- | --- |
| Complexity | High — four scripts, external state, composite digest |
| Auditability | Excellent — every decision traceable via transaction key |
| Idempotency | Strong — tree SHA verification, full workspace rollback |
| Team familiarity | Moderate — PowerShell + Python hybrid requires cross-stack knowledge |

Pros: Deterministic identity prevents collisions. Self-invalidating cache prevents stale approvals. PR-gated promotion preserves human authority. External state keeps repo pristine.
Cons: Higher initial implementation effort. PowerShell + Python boundary requires careful error code propagation. Composite digest must be maintained as pipeline components evolve.


#### Option B: Simple Hash-and-Promote


| Dimension | Assessment |
| --- | --- |
| Complexity | Low — single script, file-hash based skip logic |
| Auditability | Weak — no transaction key, no context awareness |
| Idempotency | Fragile — duplicate branches possible on retry |
| Team familiarity | High — straightforward scripting |

Pros: Fast to build. Easy to understand. Minimal moving parts.
Cons: Policy changes do not trigger re-evaluation. Filename collisions across directories. No audit trail. Retry safety depends on manual cleanup. Not suitable for enterprise-grade governance.


#### Option C: CI/CD Platform Plugin (GitHub Actions / Jenkins)


| Dimension | Assessment |
| --- | --- |
| Complexity | Medium — pipeline-as-code in YAML |
| Auditability | Moderate — CI logs serve as audit, but no structured ledger |
| Idempotency | Platform-dependent — varies by CI system |
| Team familiarity | Moderate — depends on existing CI stack |

Pros: Leverages existing CI infrastructure. Built-in retry and logging.
Cons: Gitea CI is less mature than GitHub Actions. Transaction identity must still be custom-built. External state management is not native to CI platforms. Vendor lock-in to CI platform semantics.

### Trade-off Analysis

The fundamental trade-off is implementation complexity vs. governance strength. Option A requires the most upfront investment but is the only option that provides deterministic identity, self-invalidating cache, and mathematical proof (via tree SHA) that the remote state matches local intent. Given that this system is the governance boundary for AI-generated content entering a knowledge base, the additional complexity is justified — the cost of a governance failure (stale approval, collision, orphaned state) exceeds the cost of building the control plane correctly.

### Consequences

- Easier: Adding new validation rules (update _policy_bundle.md; the digest auto-invalidates). Auditing promotion decisions. Retrying failed runs. Detecting stale evaluations.
- Harder: Onboarding new contributors to the pipeline (requires understanding PowerShell + Python + Git internals). Debugging cross-layer failures. Porting to non-Windows environments.
- Revisit: Managed provider rotation or multi-provider failover. Self-hosted model specialization (LoRA/DPO, see Part 7). Linux portability (requires replacing PowerShell orchestration). Multi-model consensus (requires schema extension).


## Part 3: Implementation Roadmap

*Now / Next / Later prioritization with dependencies and capacity notes*


### NOW — Foundation (Weeks 1–3)

Committed work. These items establish the identity layer and core evaluation loop.

| # | Item | Component | Dependencies | Acceptance |
| --- | --- | --- | --- | --- |
| 1 | Build parse_identity.py with UTF-8 BOM handling and stable JSON output | parse_identity.py | None — start here | Extracts source_id from frontmatter; handles BOM; returns structured JSON on success and failure |
| 2 | Update validator_runner.py to use parse_identity.py as parser authority | validator_runner.py | Item 1 | Imports parse_identity; no duplicate regex; distinct exit codes for full 0–5 contract (APPROVE/REJECT/ESCALATE/SCHEMA_FAULT/SYSTEM_FAULT/TOKEN_OVERFLOW) |
| 3 | Update Run-Validator.ps1 to build transaction keys from parser output | Run-Validator.ps1 | Items 1, 2 | Context digest computed; ledger keys use canonical form; startup reconciliation persists immediately |
| 4 | Create validation_result.schema.json | Schema artifact | None — parallel with Item 1 | Covers approve/reject/escalate outcomes; validator_runner validates output against it |
| 4b | Create ops/validator_config.json (model configuration manifest) | Config artifact | LLM provider decision (Open Question #1 — **resolved Phase 1.3**) | Contains provider, model_id, quantization_level, temperature, top_p, max_context_tokens, system_instruction_hash, lora_adapter_path (null for v1), tokenizer_id; all fields except tokenizer_id included in context digest. Config now targets anthropic/claude-sonnet-4-6. |
| 4c | Implement JSON-structured logging (JSONL to C:\llm-wiki-state\logs\pipeline.log) | Run-Validator.ps1 | None — parallel with Item 1 | Heartbeat + transaction entries; Try/Catch wrapper on top-level loop; SYSTEM_FAULT exits write to error log |
| 4d | Token budget enforcement in validator_runner.py with EXIT_TOKEN_OVERFLOW (code 5) | validator_runner.py | Item 4b (model config defines context window) | Pre-send token count; policy_bundle + article must fit model context window; overflow handled as non-terminal skip |
| 4e | Bootstrap golden corpus: curated examples covering approve/reject/escalate + adversarial edge cases | Test artifact | None — parallel with Item 1 | Mixed-source: manually curated + synthetic adversarial; overrepresents malformed frontmatter, policy conflicts, near-limit tokens, ambiguous cases |
| 4f | Runtime parity harness: managed vs. self-hosted agreement testing on golden corpus | Test harness | Items 2, 4b, 4e | Both model paths evaluate same corpus; decision agreement rate computed; threshold gates self-hosted activation |


### NEXT — Promotion & Integrity (Weeks 4–6)

Planned work. Builds the promotion gateway and hardening layer on top of the foundation.

| # | Item | Component | Dependencies | Acceptance |
| --- | --- | --- | --- | --- |
| 5 | Build Promote-ToVerified.ps1 with namespace preservation and tree SHA verification | Promote-ToVerified.ps1 | Items 1–4 complete | Mirrors provisional path under verified/; verifies remote PR equivalence via tree SHA; full workspace rollback on fast-path |
| 6 | Build _policy_bundle.md v1 with initial content policy rules | policy_engine/ | Product sign-off on policy criteria | Covers accuracy, completeness, and formatting standards for wiki articles |
| 7 | End-to-end test suite: approve, reject, escalate, schema fault, idempotent retry, declined PR, injection | Test harness | Items 1–6 | All 8 test matrix scenarios (T1–T8) pass including declined PR lifecycle and frontmatter injection |
| 7b | Self-hosted inference stack evaluation: vLLM vs. TGI vs. llama.cpp | Infrastructure | Item 4b (model config), parity harness results | Evaluate FlashAttention/PagedAttention support, KV cache ceiling, max concurrency per GPU, quantization quality matrix |
| 7c | Quantization evaluation: FP16 vs. Q8 vs. Q4_K_M on golden corpus | Evaluation artifact | Items 4e, 4f, 7b | Measure decision agreement rate vs. managed API at each quantization level; document quality/cost trade-off |


### LATER — Operational Maturity (Weeks 7+)

Directional. Scope and timing flexible based on learnings from NOW and NEXT.

| # | Item | Category | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| 8 | Rejection feedback sidecar files for content authors | P1 feature | Core pipeline operational | Write structured feedback to provisional/ alongside rejected drafts |
| 9 | Pipeline metrics dashboard (throughput, latency, rejection rate) | P1 feature | Ledger data available | Read-only view of validation_state.json for operational visibility |
| 10 | Vertex AI regime classification integration | P2 feature | Runner model config externalized | Requires model provider abstraction in validator_runner.py |
| 11 | Fine-tuning decision gate: compare prompt-only vs. fine-tuned accuracy on production holdout set | Evaluation | Sufficient human-reviewed pipeline data (est. 500+ transactions) | If fine-tuned model exceeds prompt-only by >5% agreement on holdout, proceed to LoRA/QLoRA adaptation |
| 12 | LoRA/QLoRA fine-tuning on pipeline evaluation data | Model adaptation | Item 11 decision gate passes; ledger has sufficient structured payloads | Train LoRA adapter on human-reviewed outcomes; merge into self-hosted model; re-run parity harness |
| 13 | DPO alignment from PR review outcomes | Model adaptation | Item 12 complete; reviewer merge/decline data accumulated | Train on preference pairs (merged PR = positive, declined PR = negative); validator improves from its own audit trail |
| 14 | Rolling holdout set: frozen evaluation slice refreshed on cadence, never used for tuning | Evaluation infrastructure | Production corpus sufficiently large | Immutable holdout prevents overfitting; used only for parity testing and regression detection |


### Risks & Dependencies


| # | Risk | Impact | Mitigation |
| --- | --- | --- | --- |
| R1 | Managed API provider and self-hosted parity candidate selection blocks validator_runner.py | Delays items 2–7 | Resolve both selections in Week 1; runner already designed with provider abstraction via validator_config.json |
| R2 | Gitea branch protection config unknown | May require promotion script rework | Document current Gitea config before starting Item 5 |
| R3 | PowerShell + Python cross-layer error propagation | Silent failures if exit codes are lost | Exit code contract defined (0–5, see Part 7); test boundary failures explicitly in Week 1 |
| R4 | Fast-path cleanup drift (LLM_WIKI_CONTROL_PLANE_REVIEW.md § Remaining Risks) | Orphaned workspace state | Add cleanup verification to test suite (Item 7); run as post-promotion assertion |


## Part 4: Design-Phase Code Review

*Architecture & invariants, implementation readiness, security & trust model, test coverage strategy*


### Review Summary

This review evaluates the design artifacts in LLM Content Pipeline Hardening.md and LLM_WIKI_CONTROL_PLANE_REVIEW.md against four dimensions: architectural soundness, implementation readiness, security posture, and test strategy. The design is strong in the areas that matter most. The remaining gaps are well-contained and addressable during implementation.
**Verdict:** Approve with conditions — proceed to implementation after resolving the two blocking open questions (LLM provider, Gitea branch protection config). *Update (Phase 1.3): LLM provider question resolved — Anthropic Claude Sonnet 4.6 selected (ADR-004).* *Update (Phase 1.5): Gitea branch protection config resolved — `enable_push=false`, `required_approvals=1` on an external Gitea instance (private, not included in this repository) (OQ-2). Both blocking conditions now cleared.*

### Architecture & Invariants


#### What Looks Good

- The five critical invariants (single parser, path-bounded promotion, external state, context-aware cache keys, namespace preservation) are well-defined and mutually reinforcing. Each invariant addresses a specific failure mode documented in the hardening conversation.
- The composite context digest is a particularly strong design choice. By including all logic, identity, rules, and state inputs in a single SHA256 hash, the system becomes self-correcting when any part of the control plane changes.
- The component responsibility map (Run-Validator, parse_identity, validator_runner, Promote-ToVerified) has clean boundaries. Each component has a single SSoT authority, preventing split-brain disagreements.

#### Critical Issues


| # | Issue | File Reference | Severity | Recommendation |
| --- | --- | --- | --- | --- |
| C1 | Context digest does not include Gitea branch-protection state. Server-side policy changes are invisible to the local digest. | LLM_WIKI_CONTROL_PLANE_REVIEW.md § Remaining Risk 4 | 🟡 Medium | Document the limitation explicitly in the runbook. Consider a periodic Gitea API check as a P1 enhancement. |
| C2 | The design specifies PowerShell calling Python via shell-out. The exit code contract (0–5) is now defined in Part 7 but must be tested at the cross-layer boundary. | Both design docs; Part 7 § Exit Code Contract | 🟡 Medium | Exit code enum is defined: 0=APPROVE, 1=REJECT, 2=ESCALATE, 3=SCHEMA_FAULT, 4=SYSTEM_FAULT, 5=TOKEN_OVERFLOW. Remaining risk: test each code path at the PowerShell–Python boundary to ensure Python exit codes are not collapsed to a generic non-zero. |


### Implementation Readiness

The design documents provide enough specificity to begin implementation, with two notable gaps:
- The validation_result.schema.json is referenced but not yet defined. This is the single most important artifact to nail down early because both validator_runner.py and Run-Validator.ps1 depend on its shape. Recommendation: Create the schema as the first deliverable alongside parse_identity.py.
- The _policy_bundle.md format and structure are not specified. The pipeline will evaluate content against this bundle, but the review documents do not define what a policy rule looks like, how rules are versioned, or how the LLM prompt is constructed from the bundle. Recommendation: Define a minimal policy bundle format during the NOW phase and expand iteratively.

#### Implementation-Ready Components


| Component | Readiness | Gap |
| --- | --- | --- |
| parse_identity.py | ✅ Ready — requirements fully specified (UTF-8 BOM, stable JSON schema, BOF frontmatter only) | None |
| validator_runner.py | 🟡 Mostly ready — requires schema definition and managed/self-hosted provider selection | Schema + provider selection (managed primary, self-hosted parity candidate) |
| Run-Validator.ps1 | 🟡 Mostly ready — requires schema definition for ledger state shape | Ledger format finalization |
| Promote-ToVerified.ps1 | 🟡 Mostly ready — Gitea config resolved (Phase 1.5); env-driven client layer and preflight checks implemented. Remaining: local git operations (branch/copy/commit/push), tree-SHA equivalence (P0-8), workspace rollback (F7) | Implementation of git push path and rollback |


### Security & Trust Model


#### Strengths

- LLM output is untrusted by design. Every claim from the model is validated against validation_result.schema.json before any downstream action. This is the correct default posture for any system that consumes LLM output.
- Force-push has been explicitly eliminated. The promotion script reconciles remote state before pushing and uses tree SHA comparison to detect tampering. This prevents a class of attacks where a compromised remote branch could be silently overwritten.
- PR-based promotion preserves human authority. The automation creates PRs but never merges directly to main. This is the right boundary for an AI-assisted content system.
- State isolation: All pipeline metadata (ledger, audit logs, PR tracking) lives outside the repo at C:\llm-wiki-state\. This prevents metadata from polluting the content repository and eliminates merge conflicts with pipeline state.

#### Suggestions


| # | Finding | Category | Recommendation |
| --- | --- | --- | --- |
| S1 | Gitea API token for PR creation is not discussed in the security model | Auth / Secrets | Store token in a secrets manager or env var; never in script files or repo. Document rotation cadence. |
| S2 | The ledger at C:\llm-wiki-state\ has no access controls specified | Data integrity | Restrict write access to the service account running the pipeline. Consider file-level integrity hashing. |
| S3 | LLM prompt injection via malicious frontmatter in provisional files | Input validation | parse_identity.py must enforce: source_id matches restricted identifier format ^[a-zA-Z0-9-]{1,36}$ (alphanumeric + hyphen, max 36 chars); all frontmatter values capped at 256 bytes; validation failure returns structured error JSON and triggers SYSTEM_FAULT exit code. No raw frontmatter values pass to the LLM prompt unsanitized. |


### Test Coverage Strategy

The test matrix in LLM_WIKI_CONTROL_PLANE_REVIEW.md defines six scenarios. This is a strong start. Below is a recommended extension organized by test pyramid layer.

#### Unit Tests (parse_identity.py, validator_runner.py)

- Valid frontmatter: standard YAML with source_id present
- UTF-8 BOM frontmatter: source_id still extracted correctly
- Missing frontmatter: returns structured error, does not crash
- Malformed YAML: returns structured error with parse details
- Schema validation: LLM output missing required fields triggers schema_fault
- Schema validation: LLM output with out-of-range scores triggers schema_fault

#### Integration Tests (full pipeline)

These map to the six scenarios from LLM_WIKI_CONTROL_PLANE_REVIEW.md § Test Matrix, extended with workspace-cleanliness assertions:

| # | Scenario | Expected Result | Post-Condition |
| --- | --- | --- | --- |
| T1 | Same file + same context + existing open PR | No duplicate branch/PR; ledger healed | Workspace clean; no orphaned branches |
| T2 | Same file bytes + changed origin/main | Context digest changes; file re-evaluated | New ledger entry with updated digest |
| T3 | Same file bytes + changed policy bundle | Context digest changes; file re-evaluated | Previous approval invalidated |
| T4 | Two files with same basename in different directories | Both promote to distinct verified/ paths | No collision in ledger or filesystem |
| T5 | UTF-8 BOM frontmatter file | Identity parser extracts source_id | File enters normal evaluation flow |
| T6 | Remote branch exists with mismatched tree SHA | Hard failure; no ledger healing | Workspace rolled back; error logged |
| T7 | Previously declined PR (state=closed, merged=false) for same transaction key | Ledger marked declined_by_human; file skipped until doc_hash or context_digest changes | No re-promotion attempt; file remains in provisional/ |
| T8 | Frontmatter injection: source_id contains oversized string (>256 bytes) or characters outside restricted identifier format | parse_identity.py returns structured error; Run-Validator.ps1 logs SYSTEM_FAULT | Malicious file never reaches LLM evaluation |


## Part 5: Stakeholder Perspectives

*Simulated cross-functional feedback for review discussion*


### Engineering Lead Perspective

**Overall:** This is a well-designed control plane. The trust model is correct and the invariants are enforceable. My primary concern is the PowerShell-Python boundary.
The exit code contract between PowerShell and Python is the highest-risk implementation detail. The contract is now defined (0=APPROVE through 5=TOKEN_OVERFLOW, see Part 7), but if a Python exception is caught by PowerShell as a generic non-zero exit, we lose the distinction between reject, escalate, and system_fault. I would insist on boundary-testing every code path before writing any other integration code.
The tree SHA approach for remote equivalence is the right call. Commit SHAs are too volatile for idempotency checks in an automation context. I would add a logging assertion that prints the expected vs. actual tree SHA on every comparison, so debugging mismatches is straightforward.
**Ask:** Boundary tests for every exit code path (0–5) as a Week 1 deliverable.

### Product Stakeholder Perspective

**Overall:** The pipeline solves a real problem. The design is thorough. My concerns are around the author experience and visibility into pipeline decisions.
Right now, if a content author's draft is rejected, the only place to see why is the external ledger. That's an ops tool, not a user-facing experience. The P1 sidecar feedback feature should be elevated to P0 consideration, or at minimum, the rejection reason should be accessible via a simple query against the ledger without requiring direct file access.
I also want to understand the policy bundle authoring experience. Who writes _policy_bundle.md? How do they test changes before they affect all pending drafts? A policy change invalidates the entire cache, which is correct for governance but potentially disruptive if policy authors don't have a staging workflow.
**Ask:** Define the content author feedback loop (even if minimal) before shipping. Define a policy authoring and testing workflow.

### Security / Compliance Perspective

**Overall:** The trust boundaries are well-placed. LLM output untrusted by default, PR-gated promotion, externalized state. Three areas need attention.
First, the Gitea API token used for PR creation is a privileged credential that can create branches and PRs against the repo. It needs to be stored in a secrets manager, not an environment variable or config file. Rotation cadence should be documented.
Second, prompt injection via frontmatter is a real risk. If a malicious actor submits a provisional file with a source_id containing prompt injection text, parse_identity.py will faithfully extract it, and it may reach the LLM prompt. The parser should sanitize or validate the format of extracted fields.
Third, the external ledger at C:\llm-wiki-state\ should have ACLs restricting write access to the pipeline service account. If an attacker can modify the ledger, they can forge approval states.
**Ask:** Token management plan. Frontmatter sanitization in parse_identity.py. ACL specification for external state directory.

### DevOps / CI Perspective

**Overall:** The zero-footprint execution model is exactly what we want for an automation clone. The cleanup logic is thorough. A few operational concerns.
The pipeline runs as a single-instance mutex, which is fine for v1 but will become a bottleneck if content volume grows. The design should document the concurrency ceiling and what the path to parallel execution looks like (e.g., per-file locking instead of global mutex).
Monitoring and alerting are not covered in the design. If the pipeline fails silently at 3am, how do we know? At minimum, system_fault exits should write to a well-known error log that can be picked up by an alerting system.
**Ask:** Define monitoring hooks for system_fault exits. Document the concurrency ceiling and future parallelism path.


## Part 6: Failure Mode & Effects Analysis

*Systematic risk assessment mapping failure scenarios to detection, mitigation, and residual risk*

This FMEA covers the failure modes identified across the Strategy Kit, Control Plane Review, Pipeline Hardening notes, and cross-functional review feedback. Each failure mode is assessed for its detection mechanism, mitigation strategy, and residual risk after mitigation.

### Control Plane Failures


| ID | Failure Mode | Detection | Mitigation | Residual Risk |
| --- | --- | --- | --- | --- |
| F1 | LLM hallucinates or returns malformed JSON | validator_runner.py schema validation against validation_result.schema.json | EXIT_SCHEMA_FAULT (code 3); file remains in provisional/; ledger untouched | Low — prevents corrupted data from reaching verified/ |
| F2 | Context drift: model swap, temperature change, or policy update renders cached evaluations stale | Context digest mismatch on next pipeline run | Automatic cache invalidation; all pending files re-enter evaluation queue | Medium — temporary spike in API costs during mass re-evaluation |
| F3 | Stale PR: human reviewer closes/declines an automated PR without merging | Gitea API state check (state=closed, merged=false) | Ledger marked declined_by_human; file skipped until document_hash or context_digest changes | Low — requires human re-edit or policy change to re-enter queue |
| F4 | Identity collision: two files produce the same transaction key | Canonical key structure: source_id + repo_relative_path + doc_hash + context_digest | Collision probability is negligible (SHA256 space) | Negligible — mathematically improbable |


### Infrastructure Failures


| ID | Failure Mode | Detection | Mitigation | Residual Risk |
| --- | --- | --- | --- | --- |
| F5 | Gitea API is unreachable (network failure, server down) | HTTP error / timeout in Promote-ToVerified.ps1 | Full local workspace rollback; SYSTEM_FAULT logged; transaction retries on next run | Zero data loss — draft remains in provisional/, no partial state |
| F6 | LLM provider API is unreachable or rate-limited | HTTP 429/5xx or timeout in validator_runner.py | EXIT_SYSTEM_FAULT (code 4); file remains in provisional/; retry on next pipeline run | Low — evaluation deferred, not lost |
| F7 | Pipeline interruption mid-promotion (power loss, process kill) | Startup reconciliation in Run-Validator.ps1 detects orphaned state | Reconcile stale pending_pr entries; clean orphaned branches; restore workspace to main | Low — idempotent retry design handles this by construction |
| F8 | External ledger corruption or unauthorized modification | Integrity mismatch between ledger state and Git/Gitea state | ACL restrictions on C:\llm-wiki-state\; pipeline service account only. Consider file-level integrity hashing (P1). | Medium — mitigated by ACLs but no cryptographic integrity check in v1 |


### Security Failures


| ID | Failure Mode | Detection | Mitigation | Residual Risk |
| --- | --- | --- | --- | --- |
| F9 | Frontmatter injection: malicious source_id or oversized values in provisional file | parse_identity.py enforcement layer: restricted identifier regex + 256-byte cap | Structured error JSON returned; SYSTEM_FAULT exit; file never reaches LLM | Low — injection blocked at parser boundary |
| F10 | Gitea API token compromise | Anomalous PR creation patterns in audit logs | Token stored in secrets manager with documented rotation cadence; scoped to minimum required permissions | Medium — compromised token can create PRs but cannot merge (branch protection) |
| F11 | Server-side Gitea policy drift (branch protection changed without pipeline awareness) | Not detected by local context digest (documented limitation) | Documented in runbook; periodic Gitea API config check recommended as P1 enhancement | Medium — accepted risk with documented limitation |


### Model & Inference Failures


| ID | Failure Mode | Detection | Mitigation | Residual Risk |
| --- | --- | --- | --- | --- |
| F12 | Token overflow: policy_bundle + article exceeds model context window | Pre-send token count in validator_runner.py | EXIT_TOKEN_OVERFLOW (code 5); file skipped for evaluation; logged for manual review or chunking | Low — detected before API call, no wasted cost |
| F13 | Parity divergence: managed and self-hosted models produce incompatible decisions on same content | Runtime parity harness on golden corpus | Self-hosted path does not activate for production until agreement threshold met; fallback produces a new evaluation under the managed model config, and this fallback path is recorded in the ledger so there is no ambiguity about which model generated the decision | Low — gated by parity harness; divergence triggers investigation, not silent failure |
| F14 | Quantization quality regression: Q4 model drops below acceptable decision accuracy | Golden corpus agreement rate vs. FP16 baseline | Quantization evaluation matrix (roadmap Item 7c) gates deployment; fall back to higher precision or managed API; any fallback re-evaluates under the fallback model config and records the path in the ledger | Medium — quality loss is gradual and may not be detected until threshold check |
| F15 | Self-hosted GPU OOM: KV cache exhausted during concurrent evaluations | CUDA OOM error in serving stack (vLLM/TGI) | Concurrency ceiling enforced via semaphore; overflow requests queued or routed to managed API fallback (new evaluation under managed config, path recorded in ledger) | Low — bounded by serving stack configuration |
| F16 | Tokenizer mismatch: managed and self-hosted models tokenize same document differently, causing inconsistent budget calculations | Parity harness catches decision divergence; token count discrepancy logged | validator_config.json specifies tokenizer per model path; token budget uses the active model's tokenizer, not a generic one | Low — mitigated by model-specific tokenizer binding |
| F17 | LoRA adapter merge corruption: fine-tuned adapter produces degenerate outputs after merge | Post-merge parity harness on holdout set (LATER phase) | Parity harness must pass before merged model enters production; rollback to pre-merge checkpoint | Medium — mitigated by gated deployment but requires holdout set discipline |


### Risk Heat Map Summary


| Residual Risk Level | Count | Failure IDs |
| --- | --- | --- |
| Negligible | 1 | F4 (identity collision) |
| Low | 9 | F1, F3, F6, F7, F9, F12, F13, F15, F16 |
| Medium | 6 | F2, F8, F10, F11, F14, F17 |
| High | 0 | None — all high-risk modes mitigated to medium or below |


Zero failure modes remain at High residual risk across all 17 identified scenarios. The six Medium-risk items (F2, F8, F10, F11, F14, F17) are all either accepted with documentation, have P1 enhancement paths, or are gated by the parity harness before production activation. The architecture is defensible for initial deployment under hybrid model conditions.


## Part 7: LLM Infrastructure & Model Strategy

*Hybrid deployment architecture, validation runtime contract, inference requirements, and model adaptation path*


### 7.1 Hybrid Deployment ADR

**Status:** Accepted
**Date:** April 2026
**Deciders:** Josh Hillard (Owner), Engineering review

#### Context

The validator_runner.py requires an LLM to evaluate content against the policy bundle. Three deployment options exist: managed API only, self-hosted only, or hybrid. A managed-only approach is simplest but creates vendor lock-in, offers no path to specialization, and makes cost unpredictable at scale. Self-hosted-only requires significant GPU infrastructure before any evaluation can run. Hybrid provides a production-ready primary path (managed API) while building the self-hosted leg in parallel, gated by a parity harness.

#### Decision

Adopt hybrid deployment with managed API as the primary evaluation path and self-hosted open model as the secondary path. The self-hosted leg does not activate for production evaluations until the runtime parity harness demonstrates acceptable decision agreement on the golden corpus.

#### Trust Boundaries

- Both model paths are untrusted. Schema validation, exit code contracts, and ledger integration apply identically regardless of provider.
- The model path (managed vs. self-hosted) is recorded in validator_config.json and included in the context digest. Switching paths invalidates cached evaluations.
- Fallback rule: if the self-hosted path fails (OOM, timeout, parity regression), the pipeline falls back to managed API. Fallback produces a new evaluation under the managed model configuration—it does not reuse the failed self-hosted result. The fallback path is recorded in the ledger (model_path: managed, fallback_from: self-hosted, fallback_reason: <cause>), so there is no ambiguity about which model generated the decision. Fallback does not require manual intervention.

#### Parity Requirements

The self-hosted leg is gated by a runtime parity harness that evaluates both model paths against the same golden corpus. The harness measures decision agreement rate (approve/reject/escalate concordance) and score distribution similarity. The self-hosted path activates for production only when agreement exceeds a defined threshold (recommended: 90% decision agreement on the golden corpus).


### 7.2 NOW: Validation Runtime Contract

These items are implementation requirements for the current phase, blocking or parallel with the core pipeline build.

#### validator_config.json Specification

This file is the System Configuration Manifest for the validation runtime. It is included in the context digest SHA256 concatenation. Any change to this file invalidates all cached evaluations.

| Field | Type / Example | Impact on Digest |
| --- | --- | --- |
| provider | "vertex_ai", "openai", "anthropic", "self_hosted" | Yes — switching provider invalidates cache |
| model_id | "gemini-1.5-pro", "llama-3.1-70b" | Yes — model swap invalidates cache |
| quantization_level | "fp16", "q8", "q4_k_m", null (managed) | Yes — quantization affects output quality |
| temperature | 0.0 – 1.0 | Yes — affects evaluation determinism |
| top_p | 0.0 – 1.0 | Yes |
| max_context_tokens | 128000 (model-specific) | Yes — defines token budget ceiling |
| system_instruction_hash | SHA256 of the system prompt template | Yes — prompt changes invalidate cache |
| lora_adapter_path | null (v1), "adapters/wiki-eval-v1" (post-LoRA) | Yes — adapter changes invalidate cache |
| tokenizer_id | Model-specific tokenizer identifier | No — derived from model_id, but explicit for budget calculation |


#### Token Budget Enforcement

validator_runner.py must compute the token count of (system_instruction + policy_bundle + article_content) using the active model’s tokenizer before sending the request. If the total exceeds max_context_tokens minus a response reserve (recommended: 2048 tokens), the file triggers EXIT_TOKEN_OVERFLOW (code 5) and is skipped for evaluation.
This is critical in hybrid deployment because managed and self-hosted models use different tokenizers. The same 8,000-word article may consume 10,200 tokens under one tokenizer and 11,400 under another. The budget check must use the tokenizer bound to the active model path, not a generic estimate.

#### Exit Code Contract (Updated)


| Code | Meaning | Pipeline Behavior |
| --- | --- | --- |
| 0 | APPROVE | File enters promotion via Promote-ToVerified.ps1 |
| 1 | REJECT | Ledger updated; file remains in provisional/ |
| 2 | ESCALATE | Ledger updated; routed for human review |
| 3 | SCHEMA_FAULT | LLM output failed schema validation; non-terminal |
| 4 | SYSTEM_FAULT | Infrastructure failure (API down, timeout); retry next run |
| 5 | TOKEN_OVERFLOW | Document exceeds context window; skipped, logged for manual review |


#### Golden Corpus Specification

The golden corpus is the foundation for the parity harness and all future model evaluation. It is a mixed-source, adversarially overrepresented test set that must exist before the parity harness can produce meaningful results.

#### Phase 0: Bootstrap Corpus (NOW)

Manually curated examples from any trustworthy source, including synthetic adversarial cases. Must cover all three decisions (approve, reject, escalate) and overrepresent edge cases:
- Malformed frontmatter (missing source_id, invalid YAML, BOM variants)
- Policy conflicts (article contradicts policy bundle rules)
- Factual contradictions (internally inconsistent claims)
- Incomplete articles (missing sections, truncated content)
- Token overflow / near-limit prompts (articles at 95%+ of context window)
- Same content under different context digests (policy change simulation)
- Ambiguous cases where human escalation is the correct answer

#### Phase 1: Production Corpus (NEXT)

Human-reviewed real drafts and PR outcomes from the live pipeline. As the system runs and reviewers merge or decline automated PRs, those outcomes become ground-truth labels. This set grows organically and replaces the synthetic bootstrap cases over time.

#### Phase 2: Rolling Holdout (LATER)

A frozen evaluation slice refreshed on a defined cadence (recommended: quarterly), never used for tuning. This holdout is the immutable parity benchmark. It prevents overfitting during LoRA/DPO adaptation and provides a stable regression detection surface. When the holdout is refreshed, the previous version is archived for longitudinal comparison.


### 7.3 NEXT: Self-Hosted Inference Requirements

These items become active once the managed API primary path is operational and the golden corpus exists. The goal is to evaluate whether the self-hosted leg can meet the parity and performance requirements for production activation.

#### Serving Stack Evaluation


| Stack | FlashAttention | PagedAttention | KV Cache Mgmt | Notes |
| --- | --- | --- | --- | --- |
| vLLM | Yes (FlashAttention-2) | Yes (native) | Automatic paging; configurable GPU memory utilization | Best throughput for batched inference; Python-native; active development |
| TGI | Yes | Yes (continuous batching) | Automatic; tensor parallelism for multi-GPU | HuggingFace ecosystem; good for rapid prototyping |
| llama.cpp | Partial (Metal/CUDA) | No | Static allocation; no dynamic paging | Best for CPU/consumer GPU; GGUF quantization; lowest ops complexity |


#### Attention Architecture Considerations

The choice of self-hosted model is constrained by attention architecture. Models with grouped-query attention (GQA) like Llama 3 use significantly less KV cache memory per token than models with full multi-head attention (MHA), enabling longer context windows on the same GPU hardware. For wiki article evaluation where documents can be 5,000–20,000 tokens, GQA models are strongly preferred for the self-hosted leg.
FlashAttention-2 reduces peak GPU memory during the attention computation itself, enabling either larger batch sizes or longer sequences. PagedAttention (vLLM) addresses a different bottleneck: it prevents KV cache fragmentation across variable-length requests, allowing the serving stack to handle concurrent evaluations of different-length articles without wasting GPU memory on padding. Both are relevant for a pipeline that batches 10–50 files per run with highly variable document lengths.

#### Quantization Evaluation Matrix

Before the self-hosted leg activates for production, the following matrix must be evaluated on the golden corpus:

| Level | VRAM (70B) | Expected Quality | Throughput | Decision Gate |
| --- | --- | --- | --- | --- |
| FP16 | ~140 GB (multi-GPU) | Baseline (reference) | Lowest | Baseline for agreement comparison |
| Q8 | ~70 GB (single A100) | Near-baseline (<1% degradation typical) | Moderate | Acceptable if agreement >95% vs. managed API |
| Q4_K_M | ~35 GB (single A100 or dual consumer) | Measurable degradation on nuanced tasks | Highest | Acceptable only if agreement >90% vs. managed API on golden corpus |


#### Concurrency Ceiling

The single-instance mutex in Run-Validator.ps1 is a pipeline-level constraint. The self-hosted inference stack adds a GPU-level constraint: KV cache memory limits how many concurrent evaluation contexts the GPU can hold. For a 70B Q4_K_M model on a single A100 (80GB), with 35GB for model weights and 45GB for KV cache, the practical concurrency ceiling is approximately 4–8 simultaneous 16K-token evaluations. The pipeline should document this ceiling and the path to parallelism (per-file locking + inference queue).


### 7.4 LATER: Model Adaptation

These capabilities depend on accumulated production data and are gated by decision thresholds. The key principle: DPO and LoRA influence what you log now, but not what you build now.

#### Fine-Tuning Decision Gate

After the pipeline has accumulated sufficient human-reviewed transactions (recommended minimum: 500), evaluate whether fine-tuning outperforms prompt-only evaluation:
- Run prompt-only model on production holdout set. Record decision agreement with human reviewers.
- Fine-tune via LoRA on human-reviewed outcomes. Run fine-tuned model on same holdout.
- If fine-tuned exceeds prompt-only by >5% decision agreement, proceed to production deployment of the adapter.
- If delta is <5%, the policy bundle prompt approach is sufficient. Re-evaluate after the next 500 transactions.

#### LoRA / QLoRA Path

LoRA (Low-Rank Adaptation) trains ~1–2% of the model’s parameters by injecting low-rank matrices into the attention layers. QLoRA extends this to quantized base models, enabling fine-tuning of a 70B model on a single consumer GPU. For this pipeline:
- Training data: structured evaluation payloads from the ledger (full model output + human reviewer outcome)
- Adapter output: a small LoRA checkpoint (~100–500 MB) that merges with the base model at inference time
- Deployment: lora_adapter_path in validator_config.json points to the active adapter; changing this path rotates the context digest
- Safety gate: post-merge parity harness on holdout set must pass before the adapter enters production

#### DPO Alignment from PR Review Outcomes

Direct Preference Optimization trains the model on preference pairs rather than absolute labels. For this pipeline, the data source is the PR review lifecycle:
- Positive signal: reviewer merges an auto-approved PR (model’s approve decision was correct)
- Negative signal: reviewer declines an auto-approved PR (model’s approve decision was wrong)
- Training pairs: (approved-then-merged output, approved-then-declined output) for the same content type
This creates a flywheel where the pipeline’s own audit trail becomes training data, and the model improves from the corrections humans make to its decisions. The ledger retention requirement (P0-14) ensures this data is available from day one, even though DPO training is a LATER-phase capability.

#### Ledger Retention for Training Data

To support future LoRA/DPO adaptation, each ledger entry must retain (from day one):

| Field | Content | Training Use |
| --- | --- | --- |
| transaction_key | Canonical key (source_id + path + hash + digest) | Deduplication and lineage |
| model_config_snapshot | Full validator_config.json at evaluation time | Attribute outcomes to specific model configurations |
| full_model_output | Complete LLM response (not just approve/reject) | Input for LoRA supervised fine-tuning |
| schema_validated_result | Parsed evaluation against validation_result.schema.json | Structured labels for training |
| reviewer_outcome | merged, declined, or pending (updated async after PR review) | Preference signal for DPO pairs |
| reviewer_timestamp | When the PR was merged or declined | Temporal ordering for holdout splits |
| article_token_count | Token count under the active tokenizer | Filter training data by document length characteristics |


## Revision Log


| Date | Change | Source |
| --- | --- | --- |
| April 5, 2026 | Initial strategy kit: PRD, ADR, Roadmap, Code Review, Stakeholder Perspectives | Design synthesis from LLM Content Pipeline Hardening.md and LLM_WIKI_CONTROL_PLANE_REVIEW.md |
| April 5, 2026 | Rev 2: Added Part 6 FMEA. Added P0-9 through P0-11. Added T7/T8 test cases. Expanded context digest to System Configuration Manifest. Added JSONL logging to roadmap. | Cross-functional review: model drift, PR lifecycle, injection protection, observability |
| April 6, 2026 | Rev 3: Added Part 7 (LLM Infrastructure & Model Strategy). Replaced single-provider assumption with hybrid deployment across Parts 1–6. Added P0-12 (token budget), P0-13 (parity harness), P0-14 (ledger retention for training). Added F12–F17 to FMEA. Updated ADR context/decision for hybrid. Extended roadmap NOW (4d–4f), NEXT (7b–7c), LATER (11–14). Added golden corpus spec (bootstrap, production, rolling holdout). Added serving stack evaluation, quantization matrix, exit code 5, concurrency ceiling, LoRA/QLoRA path, DPO alignment spec, ledger retention schema. | LLM infrastructure review: tokenization, attention, training, quantization, KV cache, inference optimization, model adaptation |
| April 6, 2026 | Rev 3.1: Editorial cleanup. Updated Part 4 exit codes from 0–4 to 0–5 (reflecting Part 7 contract). Replaced stale single-provider references with hybrid framing (managed primary + self-hosted parity candidate). Added fallback implementation semantics: fallback produces new evaluation under managed config, path recorded in ledger. Narrowed Rules-of-Reality naming to control-plane + model-config digest. | Post-approval editorial review |
| April 6, 2026 | Rev 3.2: Fixed declined-PR detection from state=open to state=closed/merged=false (P0-11, F3). Replaced raw pipe delimiters in validator_config.json and ledger retention tables with commas. Widened P0-9 acceptance criteria to cover all nine validator_config.json fields. | Post-approval editorial review (round 2) |
| April 6, 2026 | Rev 3.3: Resolved tokenizer_id digest conflict (excluded from digest per Part 7 table; P0-9 updated to match). Widened roadmap 4b acceptance criteria to all nine validator_config.json fields. Changed 'UUID regex' to 'restricted identifier format' throughout (pattern is ^[a-zA-Z0-9-]{1,36}$, not a UUID spec). | Post-approval editorial review (round 3) |
| April 6, 2026 | Rev 3.4: Aligned Part 2 ADR validator_config.json field list with full 9-field contract (added max_context_tokens, tokenizer_id). Expanded roadmap item 2 exit code acceptance to include TOKEN_OVERFLOW (0–5). Markdown formatting cleanup. | Post-approval editorial review (round 4) |
