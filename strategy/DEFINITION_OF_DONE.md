# Definition of Done — Standard Quality Gates

**Version:** 1.0
**Status:** Design — Pre-Implementation
**Date:** April 6, 2026
**Owner:** Josh Hillard
**Source Authority:** Strategy Kit Rev 3.4 (Roadmap Items 1-14, FMEA F1-F17), LLM_WIKI_CONTROL_PLANE_REVIEW.md (Critical Invariants 1-5), TELEMETRY_SPEC.md, CORPUS_MAINTENANCE_SOP.md


## Purpose

This document establishes the standard quality gates that every roadmap item must satisfy before it is considered complete. No roadmap item is "Done" simply because the code runs. Each item must pass all seven gates, documented with evidence, before the `PROJECT_LEDGER.md` is updated with completion status.

These gates mirror the discipline expected in a production engineering environment: deterministic testing, adversarial hardening, contract adherence, and operational observability.


## The Seven Quality Gates


### Gate 1: Logic (Success Criteria)

**Requirement:** The component passes all fixtures in the current `golden_corpus_manifest.json` with 0% regression against the Baseline Snapshot.

**What this means:** Run the full golden corpus through the pipeline (or the component under test, depending on scope). Compare every fixture's actual outcome (decision, exit code, violations) against the expected outcome defined in the manifest. Zero deviations from the baseline are acceptable.

**Baseline Snapshot:** The manifest state (`golden_corpus_manifest.json` content hash) at the completion of the *previous* roadmap item. The first roadmap item (Item 1: parse_identity.py) uses the Phase 0 seed corpus as its baseline. Each subsequent item is tested against the corpus as it existed when the prior item was marked complete.

**Evidence:** Test run output showing all fixtures evaluated, expected vs. actual results, and a pass/fail summary. Baseline snapshot hash recorded.

**Failure mode addressed:** Prevents silent regressions where a change to one component breaks behavior that was previously correct.


### Gate 2: Security (Adversarial)

**Requirement:** The component demonstrates deterministic, safe failure modes (Exit Codes 3, 4, or 5) against the full adversarial subset of the current golden corpus.

**What this means:** Run all fixtures in `golden_corpus/adversarial/` through the component. For parser-level adversarial cases (ADV-001, -002, -004, -005, -007, -008, -011), the expected outcome is exit code 4 (SYSTEM_FAULT) with structured error JSON. For ADV-014, the expected outcome is exit code 5 (TOKEN_OVERFLOW). For adversarial cases where the parser succeeds (ADV-003, -006, -009, -010, -012, -013), the expected outcome is the decision specified in the manifest — the LLM must not be confused by the adversarial content.

**Evidence:** Test run output for all adversarial fixtures, confirming that no adversarial input produces an unexpected approval, an unstructured error, or a crash.

**Failure mode addressed:** FMEA F1 (malformed LLM output), F9 (frontmatter injection), F12 (token overflow). Ensures the trust-nothing posture (ADR-001) holds under hostile input.


### Gate 3: Identity (Integrity)

**Requirement:** The component consumes `source_id` and all frontmatter metadata strictly via `parse_identity.py` output. Zero local regex or frontmatter parsing.

**What this means:** No component other than `parse_identity.py` may open a frontmatter block, extract a `source_id`, or parse YAML from an article file. This is Critical Invariant 1 from LLM_WIKI_CONTROL_PLANE_REVIEW.md. If a component needs identity data, it calls `parse_identity.py` (import or shell-out) and uses the structured JSON output.

**Evidence:** Code review confirming no duplicate parsing logic. Grep for YAML parsing, frontmatter regex, or `source_id` extraction outside of `parse_identity.py`. Zero matches outside the canonical parser.

**Verification command (indicative):**
```
grep -rn "source_id" --include="*.py" --include="*.ps1" | grep -v "parse_identity.py" | grep -v "# reference"
```

**Failure mode addressed:** Prevents split-brain identity disagreements between components (LLM_WIKI_CONTROL_PLANE_REVIEW.md § Critical Invariant 1).


### Gate 4: Telemetry (Observability)

**Requirement:** The component emits all mandatory JSONL events as defined in TELEMETRY_SPEC.md.

**What this means:** Each pipeline component has mandatory events it must emit:

| Component | Mandatory Events |
|-----------|-----------------|
| `Run-Validator.ps1` | `pipeline_started`, `reconciliation_completed`, `pipeline_completed` |
| `validator_runner.py` | `evaluation_started`, `evaluation_completed` (or `operational_fault` on exit codes 3-5) |
| `Promote-ToVerified.ps1` | `promotion_started`, `promotion_succeeded` (or `operational_fault` on failure) |
| `parse_identity.py` | No direct telemetry emission. Parser failures are captured by `validator_runner.py` as `operational_fault` events with `fault_category: "SYSTEM_FAULT"`. |

Additionally, `token_budget_exceeded` must be emitted by `validator_runner.py` when exit code 5 is triggered.

**Evidence:** Pipeline log (`C:\llm-wiki-state\logs\pipeline.log`) from the Gate 1 test run, confirming all mandatory events are present and conform to the JSONL envelope schema.

**Failure mode addressed:** Without telemetry, the system is a black box. This gate ensures that every state transition is observable and that the SLIs defined in TELEMETRY_SPEC.md can be computed from the log.


### Gate 5: Contract (API)

**Requirement:** The component adheres to the 0-5 Exit Code contract for all PowerShell-Python cross-boundary communication.

**What this means:** Every Python component that is called by a PowerShell script must return one of the six defined exit codes. PowerShell must correctly interpret each code (not collapse non-zero codes to a generic failure). The contract:

| Exit Code | Meaning | PowerShell Behavior |
|-----------|---------|---------------------|
| 0 | APPROVE | Proceed to promotion queue. |
| 1 | REJECT | Record rejection in ledger. Generate feedback sidecar. |
| 2 | ESCALATE | Record escalation in ledger. Generate feedback sidecar. |
| 3 | SCHEMA_FAULT | Log operational fault. File remains in provisional/. Ledger untouched. |
| 4 | SYSTEM_FAULT | Log operational fault. File remains in provisional/. Ledger untouched. |
| 5 | TOKEN_OVERFLOW | Log `token_budget_exceeded` and `operational_fault` events. File skipped. No API call made. |

**Evidence:** Boundary test for each exit code path. Force each code from the Python side and confirm PowerShell receives and routes it correctly. This is the "Week 1 deliverable" called out by the Engineering Lead perspective in Strategy Kit Part 5.

**Failure mode addressed:** FMEA Risk R3 (PowerShell + Python cross-layer error propagation). Strategy Kit Part 4 § C2.


### Gate 6: Audit (Ledger)

**Requirement:** The component successfully persists a full structured payload to `validation_state.json`, capturing all 7 mandatory DPO retention fields.

**What this means:** Every evaluation that produces a decision (exit codes 0, 1, or 2) must write a ledger entry containing:

1. **Transaction key** (source_id + repo_relative_path + document_hash + context_digest)
2. **Full model output** (the complete `validation_result.schema.json`-conformant response)
3. **Model configuration** (the `validator_config.json` snapshot at evaluation time)
4. **Decision** (approve, reject, or escalate)
5. **Timestamp** (ISO 8601 UTC)
6. **Model path** (managed or self-hosted)
7. **Reviewer outcome** (null at evaluation time; populated when a human merges or declines the PR)

Fault outcomes (exit codes 3-5) do not write to the ledger. The file retains its previous state or has no entry.

**Evidence:** Ledger entry from the Gate 1 test run for at least one approve, one reject, and one escalate fixture. All 7 fields present and populated (except `reviewer_outcome`, which is null until human action).

**Failure mode addressed:** P0-14 (ledger retains full structured payloads). Without complete ledger entries, the DPO/LoRA training path (Roadmap Items 11-14) has no data source.


### Gate 7: Documentation (Lineage)

**Requirement:** All new or modified functions include docstrings. `PROJECT_LEDGER.md` is updated with current metrics and phase completion details.

**What this means:**

- **Code documentation:** Every Python function and PowerShell function added or modified by the roadmap item has a docstring explaining its purpose, parameters, return value, and exit code behavior (where applicable).
- **Project ledger update:** `PROJECT_LEDGER.md` is updated with: the roadmap item number, completion date, baseline snapshot hash used for Gate 1, and any notable findings from the gate reviews (e.g., calibration issues discovered, adversarial fixtures added).

**Evidence:** Code review confirming docstring coverage. Updated `PROJECT_LEDGER.md` entry.

**Failure mode addressed:** Reduces onboarding friction (Strategy Kit ADR-001 § Consequences: "Harder: Onboarding new contributors"). Ensures the project's decision history is traceable without reading git blame.


## Gate Application by Roadmap Item

Not every gate applies with equal depth to every roadmap item. The table below shows which gates are primary (P) vs. secondary (S) for each NOW-phase item. All gates must pass, but primary gates are the focus of review effort.

| Roadmap Item | Gate 1: Logic | Gate 2: Security | Gate 3: Identity | Gate 4: Telemetry | Gate 5: Contract | Gate 6: Audit | Gate 7: Docs |
|-------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1: parse_identity.py | P | P | P | S | P | S | P |
| 2: validator_runner.py | P | P | P | P | P | P | P |
| 3: Run-Validator.ps1 | P | S | P | P | P | P | P |
| 4: validation_result.schema.json | S | S | S | S | S | S | P |
| 4b: validator_config.json | S | S | S | S | S | S | P |
| 4c: JSONL logging | S | S | S | P | S | S | P |
| 4d: Token budget enforcement | P | P | S | P | P | S | P |
| 4e: Golden corpus bootstrap | P | P | S | S | S | S | P |
| 4f: Runtime parity harness | P | P | S | P | P | P | P |


## Relationship to Other Artifacts

| Artifact | Relationship |
|----------|-------------|
| `TELEMETRY_SPEC.md` | Gate 4 requires compliance with the JSONL event schema and mandatory event list defined in the telemetry spec. |
| `GOVERNANCE_FRAMEWORK.md` | The severity-to-decision rationale informs what Gate 1 considers a "correct" decision for each fixture. |
| `FEEDBACK_SPEC.md` | Gate 5 (Contract) requires that exit codes 1 and 2 trigger feedback sidecar generation as defined in the feedback spec. |
| `CORPUS_MAINTENANCE_SOP.md` | Gate 1's baseline snapshot protocol is defined in the SOP. The snapshot hash anchors regression testing. |
| `GOLDEN_CORPUS_COVERAGE_MAP.md` | Gate 2 (Security/Adversarial) depends on the adversarial subset being comprehensive. The coverage map identifies gaps. |
| `golden_corpus_manifest.json` | Gate 1 runs against this manifest. Gate 2 runs against the adversarial subset within it. |
| `PROJECT_LEDGER.md` | Gate 7 requires an update to the ledger upon completion of each roadmap item. |
