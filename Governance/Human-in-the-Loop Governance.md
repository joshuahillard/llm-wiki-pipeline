# Human-in-the-Loop Governance

## What This Page Is

This document defines the binding governance contract between automated validation and human editorial authority in the LLM-Wiki Content Pipeline. It does not explain why human review is valuable in general. It specifies exactly where automated authority ends, where maintainer authority begins, how overrides are recorded, and what state transitions are allowed after approval, rejection, escalation, decline, or manual promotion.

This page is a control-plane contract. Any implementation of `Run-Validator.ps1`, `validator_runner.py`, promotion automation, PR reconciliation, or ledger updates must satisfy the rules below.

## Governance Invariants

1. The pipeline may evaluate content, generate structured decisions, write feedback sidecars, write decision-state ledger entries, and open promotion PRs.
2. The pipeline may not merge into `verified/`.
3. Final promotion authority is enforced mechanically by protected branches and PR-gated merge controls in Gitea.
4. Human overrides are authoritative, but they are not silent. Every override must be recorded as provenance-bearing ledger state.
5. Exit codes `0-2` are governance decisions. Exit codes `3-5` are operational faults. Governance logic applies only after a valid decision exists.
6. A declined human decision is hash-locked. The same `document_hash` under the same `context_digest` must not be re-promoted automatically.

## Authority Boundary

### What automation is allowed to decide

Automation may emit only the following decision outcomes after successful schema validation:

- `0 = approve`
- `1 = reject`
- `2 = escalate`

Automation may attach reasoning, structured policy violations, recommendations, sidecar feedback, and promotion metadata consistent with those decisions.

### What automation is not allowed to decide

Automation may not:

- merge PRs into `verified/`
- override a human decline
- re-open a promotion path for a hash-locked decline
- convert an operational fault into a decision
- conceal a disagreement between model output and human outcome

### What humans decide

Wiki Maintainers decide whether a promotion candidate actually enters `verified/`. That authority is not advisory. It is enforced by branch protection and PR merge control. The pipeline ends at PR creation and reconciliation.

## Decision Contract

### Approve

An `approve` decision means the file is eligible for promotion candidacy under the current `document_hash` and `context_digest`. It does not guarantee merge into `verified/`.

Required downstream behavior:

- write decision-state ledger entry
- emit `evaluation_completed`
- allow promotion branch creation
- allow PR creation if no hash-lock or integrity block exists

### Reject

A `reject` decision means the file does not meet the minimum bar for promotion candidacy and must remain in `provisional/`.

Required downstream behavior:

- write decision-state ledger entry
- emit `evaluation_completed`
- generate a `.feedback.md` sidecar
- prohibit promotion branch creation
- require author revision before the file can reach promotion candidacy

### Escalate

An `escalate` decision is a mandatory fail-safe for ambiguity, policy overlap, or insufficient model confidence. It is not a soft suggestion and not an operational fault.

Required downstream behavior:

- write decision-state ledger entry with `decision = escalate`
- emit `evaluation_completed`
- keep the file in `provisional/`
- generate a `.feedback.md` sidecar when author-facing remediation is required
- prohibit automatic promotion unless a maintainer performs manual promotion under the governed override path

Escalated files remain in holding state until one of the following occurs:

- the author revises the file, changing the `document_hash`
- the control plane changes, rotating the `context_digest`
- a Wiki Maintainer performs a manual promotion action

## Escalation Rules

The pipeline must escalate when governance rules require a fail-safe instead of forced approval or rejection.

Mandatory escalation triggers include:

- ambiguity between rejection and approval under the active policy bundle
- unresolved confidence threshold failure under a valid schema result
- overlapping policy signals that cannot be resolved conservatively
- three or more `minor` violations indicating systemic quality issues

Exit Code `2` must never be emitted as an approximation for a fault. If schema validation, parsing, token budgeting, or infrastructure fails, the system must emit exit code `3`, `4`, or `5` instead.

## Override and Reconciliation Contract

Human action may disagree with the model. That disagreement is a governed correction event and must be preserved as training-grade provenance.

### T7 corrected-pair contract

If a human declines a PR opened from an `approve` decision, the ledger must record a corrected pair that preserves:

- transaction key
- `document_hash`
- `context_digest`
- original model decision
- original full model output
- model configuration snapshot
- human outcome
- timestamp of human action
- provenance tag `corrected_pair`

This record is required for future DPO or LoRA adaptation. A human decline without corrected-pair retention is a governance failure.

### T8 corrected-pair contract

If a human manually promotes content that the pipeline escalated or otherwise left in `provisional/`, the ledger must record the manual outcome as a corrected pair with the same provenance requirements.

Manual promotion is authoritative, but it must remain attributable. The system must preserve both the automation outcome and the human outcome in the same audit lineage.

## Decline Hash-Lock

A maintainer decline is not a transient signal. It is a deterministic block tied to content state and control-plane state.

Required rule:

- if ledger state is `declined_by_human` for a given `document_hash` and `context_digest`, the pipeline must not create a new promotion branch or PR for that same pair

The lock is released only when:

- the file changes, producing a new `document_hash`, or
- the control plane changes, producing a new `context_digest`

The pipeline must not treat elapsed time, repeated runs, or operator convenience as a reason to bypass the lock.

## Feedback Delivery Contract

Governance is not complete when a file is rejected or escalated. The author must receive actionable remediation data.

### Sidecar requirement

For every rejected file, a `.feedback.md` sidecar is mandatory.

For escalated files, a `.feedback.md` sidecar is required whenever the outcome is being returned to the author for remediation rather than held solely for maintainer review.

The feedback sidecar must conform to the projection rules in [FEEDBACK_SPEC.md](../strategy/FEEDBACK_SPEC.md), including:

- structured rule IDs
- author-facing action guidance
- line-level or section-level references when available
- `frontmatter` locations for parser-originated violations

No rejection workflow is complete unless author-visible feedback exists.

### Location contract

Line and section references are post-processing outputs, not raw model authority. The governance layer depends on these references for author remediation quality, but their computation remains a validator responsibility rather than a model-owned field.

## Holding-State Contract

Files in governance holding states must remain observable and deterministic.

### Rejected files

Rejected files remain in `provisional/` with feedback sidecars until the author revises and recommits them.

### Escalated files

Escalated files remain in `provisional/` and in decision-state ledger history until:

- revised by the author
- manually promoted by a maintainer
- invalidated by context rotation and re-evaluated

### Declined PRs

Declined promotion candidates are recorded as `declined_by_human` and blocked by hash-lock rules. They do not re-enter promotion automatically.

## Ledger Retention Contract

Governance records are future training data and audit evidence. The ledger must preserve enough information to reconstruct both the automated and human decision paths.

At minimum, governance-grade retention must preserve:

- transaction key
- full model output
- model configuration snapshot
- decision
- timestamp
- model path or provider path
- reviewer outcome

If a human override occurs, the retained record must also preserve the provenance tag `corrected_pair`.

## Telemetry and Auditability

Human-in-the-loop governance depends on both ledger state and operational telemetry.

Required audit behavior:

- decision outcomes `0-2` emit `evaluation_completed`
- operational faults `3-5` emit `operational_fault`
- append-only telemetry must not be used to overwrite or erase prior governance evidence
- reconciliation steps must preserve the relationship between decision telemetry, PR state, and ledger state

Important constraint:

`escalate` is a decision outcome, not a `fault_category`. Escalated files are governed holding states, not operational failures.

## Failure Modes This Contract Prevents

- silent human overrides that cannot be used for adaptation
- repeated promotion attempts against the same declined content
- rejected files with no actionable author feedback
- escalation outcomes that disappear into indefinite limbo with no recorded state
- automation overstepping branch-protected human authority
- audit trails that preserve only the final answer and lose the disagreement

## Implementation Checklist

- protected branches are the deterministic enforcement point for human merge authority
- `approve`, `reject`, and `escalate` are the only governance decisions
- rejected files always receive `.feedback.md`
- escalated files remain in `provisional/` until revision, context rotation, or manual promotion
- human declines write `declined_by_human` against the current `document_hash` and `context_digest`
- the same hash/digest pair cannot be re-promoted automatically
- human overrides record `corrected_pair` provenance
- ledger retention preserves the minimum governance training fields
- telemetry remains append-only and consistent with decision versus fault semantics

## Related Pages

- [LLM System Trust Model.md](../Foundations/LLM System Trust Model.md)
- [Trust Boundaries in LLM Pipelines.md](../Foundations/Trust Boundaries in LLM Pipelines.md)
- [Transaction Identity and Auditability.md](../Foundations/Transaction Identity and Auditability.md)
- [Schema Validation for LLM Output.md](../Foundations/Schema Validation for LLM Output.md)
- [FEEDBACK_SPEC.md](../strategy/FEEDBACK_SPEC.md)
- [GOVERNANCE_FRAMEWORK.md](../strategy/GOVERNANCE_FRAMEWORK.md)
- [TELEMETRY_SPEC.md](../strategy/TELEMETRY_SPEC.md)
