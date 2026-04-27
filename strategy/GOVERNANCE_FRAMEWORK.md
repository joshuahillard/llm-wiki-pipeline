# Governance Framework

**Version:** 1.0
**Status:** Design — Pre-Implementation
**Date:** April 6, 2026
**Owner:** Josh Hillard
**Source Authority:** VIOLATION_TAXONOMY.md, Strategy Kit Rev 3.4 (PRD Goals, ADR-001, FMEA), LLM_WIKI_CONTROL_PLANE_REVIEW.md


## Purpose

This document defines the editorial philosophy and governance rationale behind the LLM-Wiki Content Pipeline's automated content validation. It answers three questions the VIOLATION_TAXONOMY alone cannot: **why** these rules exist, **where** automated judgment ends and human authority begins, and **how** severity levels map to pipeline decisions.

This is a one-page governance artifact, not a compliance framework. It provides the intellectual scaffolding for anyone reviewing the taxonomy, the golden corpus, or the pipeline's decision logs.


## Editorial Philosophy

The wiki exists to be a trusted knowledge substrate. Every article in `verified/` represents a claim that the content has been evaluated against a defined standard and found to be accurate, complete, and safe for consumption. The pipeline does not generate content — it governs the boundary between draft and canonical.

Three principles guide the evaluation criteria:

**1. Accuracy over completeness.** A short, correct article is preferable to a comprehensive article with factual errors. This is why ACCURACY violations carry `critical` severity (mandatory rejection) while COMPLETENESS violations are `major` (rejection with escalation path). An incomplete article wastes a reader's time; an inaccurate article corrupts their understanding.

**2. Safety is non-negotiable.** SECURITY violations (credentials, PII, internal infrastructure details) are always `critical`. There is no context in which hardcoded credentials or personally identifiable information should pass through an automated content gate. This aligns with the trust-nothing security posture defined in ADR-001.

**3. Judgment calls belong to humans.** When the LLM cannot confidently determine whether content is accurate, complete, or neutral, the correct response is escalation (Exit Code 2), not a forced decision. The pipeline is designed to be conservative: it should reject what it knows is wrong and escalate what it cannot resolve, rather than approving under uncertainty.


## Severity-to-Decision Rationale

The VIOLATION_TAXONOMY defines four severity levels. This section explains how they map to the pipeline's three decision outcomes and the reasoning behind each mapping.

### Critical → REJECT (Exit Code 1)

Any single `critical` violation forces rejection. This applies to:

- **ACCURACY-001** (inverted factual claims) and **ACCURACY-005** (internal contradictions): These represent content that is demonstrably wrong. Promotion would place known falsehoods in the verified corpus.
- **SECURITY-001** (hardcoded credentials) and **SECURITY-003** (PII): These represent content that is dangerous regardless of its informational quality. No amount of otherwise-good content overrides a credential leak.

The rationale is binary: if the content is provably wrong or provably unsafe, the pipeline must not promote it. There is no reviewer override at the automation layer — a rejected file must be revised and re-committed by the author.

### Major → REJECT or ESCALATE (Exit Codes 1 or 2)

`Major` violations generally produce rejection, but the pipeline allows escalation when the violation is ambiguous or context-dependent. This applies to:

- **ACCURACY-002** (outdated information): A reference to a deprecated tool is usually grounds for rejection, but edge cases exist (e.g., an article documenting historical tooling for migration purposes). The LLM should reject clear cases and escalate borderline ones.
- **COMPLETENESS-001/002/003** (TODOs, empty sections, stubs): These are always rejection-worthy in isolation. However, an article with one empty section but otherwise strong content may warrant escalation rather than outright rejection.
- **SECURITY-002** (internal infrastructure details): Unlike credentials and PII, infrastructure references require context. A hostname in a networking tutorial may be synthetic; the same hostname in a deployment guide may be real. When uncertain, the pipeline escalates.

The rationale is proportional: `major` violations indicate significant issues that usually require author remediation, but the pipeline acknowledges that its confidence may be insufficient for borderline cases.

### Minor → APPROVE with Recommendations or ESCALATE (Exit Code 0 or 2)

`Minor` violations do not block promotion individually. They are noted in the `recommendations` array of the validation result. This applies to:

- **ACCURACY-004** (unverifiable quantitative claims): Stating "reduces load by 80%" without a citation is worth flagging but does not invalidate the article.
- **FORMATTING-001/002** (missing H1, broken markdown): Structural issues that affect readability but not accuracy.
- **COMPLETENESS-004** (missing expected section): A setup guide without installation steps is thin but not wrong.

When multiple `minor` violations co-occur, escalation is appropriate. The threshold is a judgment call by the LLM — the policy bundle instructs the model to escalate when three or more minor issues suggest systemic quality problems rather than isolated oversights.

### Info → APPROVE (Exit Code 0)

`Info` observations are recorded but never affect the decision. This currently includes only:

- **NEUTRALITY-001** (vendor recommendation without alternatives): Noted as an observation because vendor-specific guidance is common in technical wikis and is not inherently wrong. It becomes a concern only when combined with other quality issues.

The rationale is informational: the pipeline surfaces the observation for the author's benefit but does not treat editorial preference as a quality gate.


## Human-in-the-Loop Boundary

The pipeline creates PRs but never merges them. This is the fundamental governance boundary.

**What the pipeline decides:** Whether a draft meets the minimum bar for promotion candidacy (approve), requires author revision (reject), or exceeds the system's confidence threshold (escalate).

**What the Wiki Maintainer decides:** Whether to merge the PR. The maintainer sees the full evaluation result (decision, confidence, violations, recommendations) as PR metadata and retains final authority. An approved PR is a recommendation, not a mandate.

**What triggers re-evaluation:** A declined PR (merged=false, state=closed) is recorded in the ledger as `declined_by_human`. The file re-enters the evaluation queue only when the author revises it (changing the document hash) or when the pipeline's context digest changes (policy update, model swap). The maintainer's decline is respected — the system does not re-promote the same content against the same context.

**Escalation routing:** Escalated files (Exit Code 2) are not promoted. They are logged in the ledger with full reasoning and remain in `provisional/` until the author revises or a Wiki Maintainer manually promotes. Configurable escalation routing (P1-3) will allow specific violation categories to auto-assign reviewers in a future phase.


## Relationship to Other Artifacts

| Artifact | Relationship |
|----------|-------------|
| `VIOLATION_TAXONOMY.md` | This framework provides the "why" behind the taxonomy's severity assignments. The taxonomy is the reference implementation; this document is the rationale. |
| `validation_result.schema.json` | The schema's `decision`, `policy_violations`, and `recommendations` fields are the structured expression of the governance decisions described here. |
| `FEEDBACK_SPEC.md` | The author-facing feedback mechanism translates governance decisions into actionable remediation guidance. |
| Strategy Kit PRD (Goals) | The "100% of promotions gated by LLM validation" goal is operationalized by this governance boundary. The "60% reduction in manual review hours" goal depends on the accuracy of the severity-to-decision mapping defined here. |
| FMEA F1, F3 | F1 (malformed LLM output) is governed by the SCHEMA_FAULT path, which bypasses all governance logic. F3 (declined PR) is governed by the human-in-the-loop boundary defined above. |
