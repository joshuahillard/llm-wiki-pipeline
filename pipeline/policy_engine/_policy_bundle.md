# LLM-Wiki Policy Bundle v1

This file is the runtime policy bundle for article validation. It is intended to be read by the validator and included in the control-plane digest. It summarizes the enforceable content rules, their severity implications, and the expected decision behavior.

The taxonomy is authoritative for rule IDs. This bundle is the runtime-facing condensation of that taxonomy plus the governance framework.

## Decision Contract

Allowed decisions:

- `approve`
- `reject`
- `escalate`

Severity guidance:

- `critical` -> reject
- `major` -> reject or escalate when context is genuinely ambiguous
- `minor` -> approve with recommendations, or escalate when several minor issues indicate systemic weakness
- `info` -> approve with observations only

Conservatism rule:

- If three or more `minor` issues co-occur, prefer `escalate` rather than automatic approval.
- If the article is clearly wrong or clearly unsafe, reject.
- If the article may be acceptable but requires human judgment, escalate.

## Accuracy Rules

- `ACCURACY-001`: inverted or swapped factual claims -> `critical`
- `ACCURACY-002`: outdated guidance presented as current -> `major`
- `ACCURACY-003`: misleading oversimplification that contradicts consensus -> `major`
- `ACCURACY-004`: quantitative claims without attribution -> `minor`
- `ACCURACY-005`: internal contradiction within the article -> `critical`

Accuracy is the highest editorial priority. A short correct article is better than a detailed wrong article.

## Completeness Rules

- `COMPLETENESS-001`: explicit TODO or placeholder text -> `major`
- `COMPLETENESS-002`: empty section -> `major`
- `COMPLETENESS-003`: stub prose indicating unfinished drafting -> `major`
- `COMPLETENESS-004`: missing critical section for the article type -> `minor`

Completeness matters, but incompleteness is not always the same as inaccuracy. Use escalation when the missing material is important but the article is otherwise strong.

## Security Rules

- `SECURITY-001`: hardcoded credentials -> `critical`
- `SECURITY-002`: internal infrastructure details -> `major`
- `SECURITY-003`: PII or protected data -> `critical`

Security violations are fail-closed. Unsafe content must not be promoted.

## Formatting Rules

- `FORMATTING-001`: missing H1 -> `minor`
- `FORMATTING-002`: broken markdown -> `minor`

Formatting issues usually do not block approval on their own unless they combine with other weaknesses and materially reduce the article's usefulness.

## Neutrality Rule

- `NEUTRALITY-001`: vendor or product recommendation without alternatives or tradeoff framing -> `info`

Neutrality is observational in v1. It may be surfaced to the author, but it does not block approval by itself.

## Output Hygiene

- Emit only rule IDs that exist in the taxonomy.
- Use concise descriptions tied to the actual content issue.
- Keep recommendations actionable.
- If there are no violations, return an empty `policy_violations` array.
- Do not invent extra metadata fields.
