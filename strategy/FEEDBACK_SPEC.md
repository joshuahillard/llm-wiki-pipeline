# Feedback Specification — Author Delivery Contract

**Version:** 1.0
**Status:** Design — Pre-Implementation
**Date:** April 6, 2026
**Owner:** Josh Hillard
**Source Authority:** Strategy Kit Rev 3.4 (P1-1, User Story: Content Author), validation_result.schema.json, VIOLATION_TAXONOMY.md, GOVERNANCE_FRAMEWORK.md


## Purpose

This document defines how pipeline evaluation results are transformed from the internal `validation_result.schema.json` format into author-facing feedback. It specifies the projection logic, line-level referencing contract, delivery mechanism, and the expected remediation loop.

The Content Author user story (Strategy Kit Part 1) requires that "rejected drafts include specific reasons so that I can revise and resubmit efficiently." This spec formalizes that requirement.


## Projection Logic

The pipeline's internal evaluation result contains five fields: `decision`, `confidence`, `reasoning`, `policy_violations`, and `recommendations`. The feedback sidecar projects a subset of this data into an author-readable format, filtering out operational details (confidence scores, internal reasoning) that are meaningful to the ledger but not to the author's remediation workflow.

### What is included in feedback

| Source Field | Feedback Projection | Rationale |
|-------------|---------------------|-----------|
| `decision` | Included as header: "Result: REJECT" or "Result: ESCALATE" | The author needs to know the outcome. |
| `policy_violations[].rule_id` | Included with link to VIOLATION_TAXONOMY description | Maps the violation to a defined standard so the author understands what rule was triggered. |
| `policy_violations[].description` | Included verbatim | The LLM's explanation of where the violation occurs in this specific article. |
| `policy_violations[].severity` | Included | Helps the author prioritize which violations to fix first. |
| `recommendations[]` | Included verbatim | Actionable suggestions for remediation. |

### What is excluded from feedback

| Source Field | Reason for Exclusion |
|-------------|---------------------|
| `confidence` | Internal calibration metric. Exposing it to authors creates false precision ("the model was only 0.72 confident") without aiding remediation. |
| `reasoning` | Free-text model reasoning is retained in the ledger for DPO training (P0-14) but is often verbose and internally-focused. The `description` and `recommendations` fields provide the author-relevant subset. |


## Line-Level Referencing Contract

To enable authors to locate violations in their source file, the feedback mechanism correlates violations to specific locations in the markdown document. This is an extension to the LLM's evaluation output, not a change to `validation_result.schema.json`.

### Referencing Schema

Each violation in the feedback sidecar includes an optional `location` field:

```json
{
  "rule_id": "ACCURACY-001",
  "severity": "critical",
  "description": "TCP is described as connectionless in the 'Protocol Overview' section.",
  "location": {
    "type": "section",
    "reference": "## Protocol Overview",
    "line_start": 24,
    "line_end": 31
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `location.type` | string | One of: `section` (heading-bounded region), `line` (specific line range), `frontmatter` (YAML header). |
| `location.reference` | string | Human-readable anchor. For `section` type: the heading text. For `line` type: the first few words of the line. For `frontmatter`: the field name. |
| `location.line_start` | integer | 1-indexed line number where the violation begins. |
| `location.line_end` | integer | 1-indexed line number where the violation ends. |

### Referencing constraints

- Line numbers are computed against the file as committed to `provisional/`. If the author edits the file between commit and feedback delivery, line numbers may drift. This is an accepted limitation — the `reference` field provides a human-searchable fallback.
- The LLM prompt instructs the model to include section-level references in violation descriptions. The `line_start`/`line_end` fields are populated by a post-processing step in `validator_runner.py` that matches the LLM's section reference against the parsed markdown heading structure. If the match fails, line numbers are omitted and only the `reference` field is populated.
- Frontmatter violations from `parse_identity.py` (exit code 4) do not go through the LLM. Their location is always `{"type": "frontmatter", "reference": "<field_name>", "line_start": 1}`.


## Delivery Mechanism

Feedback is delivered through two channels, depending on the pipeline's state. Both channels render the same underlying data.

### Channel 1: Sidecar File (Primary)

For every rejected or escalated file, a `.feedback.md` sidecar is written alongside the original draft in `provisional/`.

**Naming convention:** `{original_filename}.feedback.md`

**Example:** `provisional/networking/dns.md` → `provisional/networking/dns.md.feedback.md`

**Sidecar format:**

```markdown
# Validation Feedback: dns.md

**Result:** REJECT
**Evaluated:** 2026-04-06T14:32:04Z
**Policy Version:** context digest 4af2...

## Violations

### ACCURACY-001 — Inverted factual claim (critical)

> TCP is described as connectionless in the 'Protocol Overview' section.

**Location:** `## Protocol Overview` (lines 24-31)
**Action required:** Correct the protocol description. TCP is connection-oriented; UDP is connectionless.

### COMPLETENESS-002 — Empty section (major)

> The 'Troubleshooting' section contains a heading but no content.

**Location:** `## Troubleshooting` (line 58)
**Action required:** Add troubleshooting content or remove the section heading.

## Recommendations

1. Consider adding a comparison table for TCP vs. UDP to prevent future confusion.
2. The 'Further Reading' section would benefit from links to RFC 793 and RFC 768.

---
*Generated by the LLM-Wiki Content Pipeline. See VIOLATION_TAXONOMY.md for rule definitions.*
```

**Lifecycle:** Sidecar files are overwritten on each evaluation. When the author revises the draft and re-commits, the next pipeline run produces a new sidecar (or no sidecar if the file is approved). Stale sidecars for approved files are deleted by `Run-Validator.ps1` during the post-evaluation cleanup pass.

### Channel 2: Gitea PR Comment (Secondary)

For files that reach the promotion stage but are subsequently declined by the Wiki Maintainer, the pipeline does not generate a sidecar (the file was approved by the LLM). However, the original evaluation result — including recommendations — is available as structured data in the PR metadata.

In a future phase (P1-3, escalation routing), the pipeline may post evaluation summaries as PR comments for escalated files. This spec defines the data contract; the rendering into PR comments is a P1 implementation detail.


## Remediation Loop

The expected author workflow after receiving feedback:

1. **Read sidecar.** The `.feedback.md` file appears in the same directory as the draft. The author reads the violations and recommendations.
2. **Revise draft.** The author edits the original `.md` file to address the violations. Critical violations must be resolved; minor violations are optional but recommended.
3. **Re-commit.** The author commits the revised file to `provisional/`. The commit changes the document hash, which changes the transaction key.
4. **Auto-re-evaluate.** On the next pipeline run, `Run-Validator.ps1` detects the new document hash, the cached ledger entry no longer matches, and the file re-enters the evaluation queue.
5. **New feedback or promotion.** If the revised file passes, the sidecar is deleted and the file enters the promotion queue. If it fails again, a new sidecar is written with updated violations.

There is no limit on remediation cycles. Each revision produces a new transaction key, and each evaluation is recorded in the ledger with its full payload (P0-14), creating a complete revision history per `source_id`.


## Relationship to Other Artifacts

| Artifact | Relationship |
|----------|-------------|
| `validation_result.schema.json` | The feedback sidecar is a projection of this schema. The schema is not modified — the `location` field is added during post-processing, not by the LLM's raw output. |
| `VIOLATION_TAXONOMY.md` | Rule IDs in the sidecar link back to this taxonomy. The sidecar footer directs authors to the taxonomy for full rule definitions. |
| `GOVERNANCE_FRAMEWORK.md` | The severity-to-decision rationale explains why certain violations produce rejection vs. escalation. The sidecar renders the outcome; the governance framework explains the reasoning. |
| `TELEMETRY_SPEC.md` | Sidecar generation is not a telemetry event. The evaluation that produces the feedback data is captured by `evaluation_completed` events. |
| `DEFINITION_OF_DONE.md` | This spec is a dependency for the Telemetry (Observability) gate: any component that produces rejections must trigger sidecar generation. |
| Strategy Kit P1-1 | This spec formalizes the "Structured rejection feedback written back to a sidecar file alongside the draft" requirement. |
