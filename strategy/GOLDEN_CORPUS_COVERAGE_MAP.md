# Golden Corpus Coverage Map

**Version:** 1.2
**Status:** Active — Corpus Expanded to 50 Fixtures (Phase 1.4 Calibration Rebalance)
**Date:** April 8, 2026
**Owner:** Josh Hillard
**Source Authority:** CORPUS_MANIFEST.md, corpus_manifest.json, VIOLATION_TAXONOMY.md


## Purpose

This document maps the 50 golden corpus fixtures against the five policy violation categories defined in VIOLATION_TAXONOMY.md. It identifies testing deserts — areas where the pipeline has zero or insufficient fixture coverage to validate its decision logic — and provides expansion priorities.

The heat map uses the VIOLATION_TAXONOMY as its only axis. Parser-level identity enforcements (handled by `parse_identity.py`, exit code 4) are summarized separately because they test control-plane behavior, not LLM policy judgment. LLM response-parsing tests (exit code 3, SCHEMA_FAULT) are also summarized separately because they test the validator's response-parsing logic, not policy judgment.


## Policy Violation Coverage Matrix

| Policy Category | Rule IDs | Fixture Count | Fixtures | Status |
|----------------|----------|---------------|----------|--------|
| Accuracy | ACCURACY-001 to 005 | 9 | R-001 (ACCURACY-001, -005), R-007 (ACCURACY-001, -005), R-004 (ACCURACY-002), E-005 (ACCURACY-002 borderline), E-002 (ACCURACY-003, -004), E-004 (ACCURACY-003 primary), A-009 (ACCURACY-004 non-escalation), E-001 (ambiguous accuracy, escalation), ADV-026 (ACCURACY-003 in mixed-severity cascade) | **Materially improved.** ACCURACY-004 now has a dedicated non-escalation approve fixture (A-009). ACCURACY-003 has a dedicated escalation fixture (E-004) distinct from the mixed-severity ADV-026. ACCURACY-002 now has a borderline escalation case (E-005) alongside the clear reject (R-004). ACCURACY-001 has a second reject fixture (R-007) in a different domain. |
| Completeness | COMPLETENESS-001 to 004 | 4 | R-002 (COMPLETENESS-001, -002, -003), R-006 (COMPLETENESS-001, -003), ADV-009 (COMPLETENESS-002), A-007 (COMPLETENESS-004) | **Improved.** R-006 adds a second article shape exercising COMPLETENESS-001 and -003 in a different domain (CI/CD vs. generic stubs). |
| Security | SECURITY-001 to 003 | 3 | R-003 (SECURITY-001, -002), R-005 (SECURITY-003), ADV-024 (SECURITY-001, -002, -003 via subtle PII in code), ADV-026 (SECURITY-002 in mixed cascade) | **Unchanged from Phase 1.2.** |
| Formatting | FORMATTING-001 / 002 | 2 | A-006 (FORMATTING-002), A-008 (FORMATTING-001) | **Fully covered.** A-008 closes the FORMATTING-001 desert. Both formatting rules now have dedicated fixtures. |
| Neutrality | NEUTRALITY-001 | 3 | E-003 (escalation), E-004 (secondary signal alongside ACCURACY-003), A-005 (approve with observation) | **Improved.** E-004 exercises NEUTRALITY-001 as a secondary signal in an accuracy-led escalation, adding a structurally distinct fixture shape. |


## Parser Enforcement Summary (Non-Policy)

These fixtures test `parse_identity.py` behavior before the article reaches the LLM. They are not mapped to VIOLATION_TAXONOMY rule IDs because identity enforcement is a binary gate (pass/fail), not a policy judgment.

| Category | Fixture Count | Fixtures | Coverage Assessment |
|----------|---------------|----------|---------------------|
| Missing/invalid source_id | 6 | ADV-001 (missing), ADV-004 (oversized), ADV-005 (injection in source_id), ADV-011 (special chars), ADV-021 (null literal), ADV-022 (multiline block scalar) | **Strong.** Covers regex failures, type-coercion edge cases, and YAML block scalars. ADV-021 is a regression test for the null source_id bug fix. |
| Malformed YAML | 1 | ADV-002 | **Adequate.** One fixture for YAML parse failure. |
| YAML edge cases | 2 | ADV-020 (anchor/alias attack), ADV-023 (duplicate keys) | **New category.** Tests safe_load resilience to anchors and YAML spec's last-value-wins for duplicate keys. |
| Missing frontmatter | 1 | ADV-007 | **Adequate.** Tests the "no delimiter" case. |
| Empty file | 1 | ADV-008 | **Adequate.** Tests the zero-byte boundary. |
| Parser succeeds (edge cases) | 6 | ADV-003 (UTF-8 BOM), ADV-006 (oversized value truncation), ADV-009 (no body), ADV-010 (numeric source_id coercion), ADV-012 (nested delimiters), ADV-013 (body injection) | **Strong.** Covers the key "parser succeeds but content is adversarial" paths. |
| LLM response parsing | 5 | ADV-015 (markdown-fenced valid JSON), ADV-016 (missing confidence), ADV-017 (invalid decision enum), ADV-018 (extra fields), ADV-019 (empty response) | **New category.** Tests validator_runner's response-parsing pipeline: fence stripping (ADV-015 → exit 0), schema validation failures (ADV-016/017/018 → exit 3), and unparseable input (ADV-019 → exit 3). |
| Injection resistance | 2 | ADV-013 (body injection), ADV-025 (sandwich injection between valid sections) | **Improved.** ADV-025 adds a more realistic injection vector — prompt override hidden in an HTML comment between legitimate content sections. |
| Token overflow | 1 | ADV-014 | **Adequate.** Single fixture for EXIT_TOKEN_OVERFLOW (code 5). |


## Escalation Coverage Note

Escalation (Exit Code 2) is exercised across six fixtures spanning four policy categories:

- E-001 → Accuracy (ambiguous domain knowledge trade-off)
- E-002 → Accuracy/Completeness (oversimplified claims, defensible in narrow contexts)
- E-003 → Neutrality (vendor-specific recommendations without alternatives)
- E-004 → Accuracy + Neutrality (context-dependent oversimplification as primary signal; ACCURACY-003 led)
- E-005 → Accuracy (borderline staleness; ACCURACY-002 in maintenance-mode-not-yet-EOL territory)
- ADV-026 → Accuracy + Security (good advice mixed with dangerous recommendations; mixed-severity cascade)

Escalation is a decision outcome, not a violation category. The heat map attributes escalation fixtures to the underlying policy category they exercise, per the VIOLATION_TAXONOMY's severity-to-decision mapping documented in GOVERNANCE_FRAMEWORK.md.


## Testing Deserts — Expansion Priorities

All 15 violation rule IDs in VIOLATION_TAXONOMY.md are now exercised by at least one dedicated fixture. There are no remaining testing deserts at the rule-ID level.

The previous priorities (FORMATTING-001 and ACCURACY-004 non-escalation) were closed in Phase 1.4:
- FORMATTING-001 → A-008 (approve with minor formatting observation)
- ACCURACY-004 → A-009 (approve with minor accuracy observation, non-escalation)

Remaining depth-building opportunities (not deserts):
- A dedicated reject-only ACCURACY-003 fixture (oversimplification without mixed-severity complication) would still add value beyond E-004 and ADV-026.
- COMPLETENESS-002 (empty section) has only one dedicated exercise path (ADV-009). A second fixture in a different article shape would strengthen coverage.
- SECURITY-003 is only exercised via R-005 and ADV-024. A third shape (different PII pattern) would add depth.


## Coverage Growth Targets

These targets align with PHASE0_PRIORITIES.md and CORPUS_MAINTENANCE_SOP.md:

| Milestone | Approve | Reject | Escalate | Adversarial | Total | Adversarial Ratio |
|-----------|---------|--------|----------|-------------|-------|-------------------|
| Phase 0 seed | 7 | 5+1* | 3 | 14 | 30 | 46.7% |
| Phase 1.2 | 7 | 5+1*+1 | 3+1 | 26 | 42 | 61.9% |
| **Current (Phase 1.4)** | **11** | **7+1*+1** | **5+1** | **26** | **50** | **52.0%** |
| Parity harness ready | 15+ | 15+ | 10+ | 30+ | 70+ | ~40% |

*ADV-009 (frontmatter only, no body) is counted as a reject decision because the expected outcome is `reject` with COMPLETENESS-002.

Non-adversarial bucket counts (approve/, reject/, escalate/ only): 11 approve, 7 reject, 5 escalate = 23. Total decision counts including adversarial: 16 approve, 9 reject, 6 escalate = 31.

The adversarial ratio is now 52.0% (26/50), inside the previous "after next calibration round" target of 47–53%. The next expansion round should continue prioritizing non-adversarial fixtures to move toward the ~40% parity-harness-ready target.


## Relationship to Other Artifacts

| Artifact | Relationship |
|----------|-------------|
| `CORPUS_MANIFEST.md` | The authoritative fixture list. This coverage map is derived from the manifest and will need updating when new fixtures are added. |
| `corpus_manifest.json` | The machine-checkable manifest. If this map and the JSON disagree, the JSON wins. |
| `VIOLATION_TAXONOMY.md` | The five policy categories and their rule IDs are the axis of the coverage matrix. |
| `CORPUS_MAINTENANCE_SOP.md` | Defines how corrected pairs are added to the corpus. New fixtures should target the testing deserts identified here. |
| `DEFINITION_OF_DONE.md` | Gate 1 (Logic) requires 0% regression against the corpus. Gate 2 (Security/Adversarial) requires safe failure against the adversarial subset. Both gates depend on the corpus being comprehensive enough to be meaningful. |
| `PHASE0_PRIORITIES.md` | The growth targets in this map align with the corpus growth table in PHASE0_PRIORITIES. |
