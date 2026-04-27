# Corpus Maintenance SOP — Golden Corpus Evolution

**Version:** 1.0
**Status:** Design — Pre-Implementation
**Date:** April 6, 2026
**Owner:** Josh Hillard
**Source Authority:** Strategy Kit Rev 3.4 (P0-13, Items 4e/4f, Roadmap Items 11-14), CORPUS_MANIFEST.md, golden_corpus_manifest.schema.json, GOLDEN_CORPUS_COVERAGE_MAP.md


## Purpose

This document defines how the golden corpus evolves alongside human judgment. The golden corpus is the ground truth for the parity harness (Item 4f), regression testing (DEFINITION_OF_DONE.md Gate 1), and future model adaptation (Roadmap Items 11-14). Without a defined feedback loop, the corpus fossilizes — it reflects the system's initial assumptions but not what was learned from production.

This SOP covers one process: how a human reviewer's override of an LLM decision gets promoted into the golden corpus as a "corrected pair."


## The Trigger

A corpus maintenance action is triggered when a Wiki Maintainer takes an action that contradicts the pipeline's LLM evaluation:

- **T7 scenario (Strategy Kit Part 4):** The LLM approved and created a PR, but the maintainer declines the PR. The ledger records this as `declined_by_human`. This means the LLM's approval was wrong — the file should have been rejected or escalated.
- **T8 scenario (Strategy Kit Part 4):** The LLM rejected a file, but the maintainer (after reviewing the sidecar feedback and the article) determines the rejection was incorrect and manually promotes the file. This means the LLM's rejection was wrong — the file should have been approved.

Both scenarios produce a "corrected pair": the article content, the LLM's original evaluation, and the human's override decision. This pair is the raw material for corpus expansion and future DPO training.

Detection is passive, not automated. During each corpus review cycle (recommended cadence: monthly, or after every 50 pipeline transactions, whichever comes first), the corpus maintainer queries the ledger for entries where:

```
ledger_state = "declined_by_human" OR
ledger_state = "manually_promoted"
```

These entries are candidates for corpus promotion.


## The Action

For each candidate corrected pair, the corpus maintainer performs the following:

**Step 1: Sanitize the article.** Remove any content that is specific to the production environment and would not generalize as a test fixture. Replace real credentials, hostnames, or PII with synthetic equivalents (consistent with existing adversarial fixtures like R-003). The goal is a fixture that tests the same decision boundary as the original article without carrying production data.

**Step 2: Classify the fixture.** Determine which golden corpus bucket the file belongs to based on the *human's* decision, not the LLM's:

- If the human declined an LLM approval → file goes to `reject/` or `escalate/` (depending on the reason for decline).
- If the human manually promoted an LLM rejection → file goes to `approve/`.

**Step 3: Assign an ID and add metadata.** Follow the naming convention `{BUCKET}-{NNN}-{short-description}.md`. Add the file to `golden_corpus_manifest.json` with the expected decision, expected violations (if any), and a `provenance` tag:

```json
{
  "id": "R-005",
  "file": "reject/R-005-false-approval-networking.md",
  "expected_decision": "reject",
  "expected_violations": ["ACCURACY-003"],
  "provenance": "corrected_pair",
  "source_transaction_key": "networking-dns-overview:...:9e5f...:4af2...",
  "correction_date": "2026-05-15"
}
```

The `provenance: "corrected_pair"` tag distinguishes human-corrected fixtures from the original manually-curated and synthetic-adversarial fixtures. This tag is relevant for future DPO training (Roadmap Item 13), where corrected pairs carry higher weight than synthetic examples.

**Step 4: Update CORPUS_MANIFEST.md.** Add the new fixture to the human-readable manifest with a note in the "What It Tests" column referencing the original T7/T8 scenario.

**Step 5: Validate the corpus constraint.** After adding the new fixture, verify the adversarial overrepresentation ratio.


## The Constraint

The golden corpus must maintain a minimum **30% adversarial fixture ratio** at all times. This ensures the test harness remains rigorous against malformed inputs, injection attempts, and parser boundary cases.

**Calculation:**

```
adversarial_ratio = count(adversarial/*) / count(all fixtures) * 100
```

**Current state (26 fixtures):** 14 adversarial / 26 total = 53.8%. Well above the 30% floor.

**Growth scenario:** As corrected pairs are added (primarily to approve/, reject/, and escalate/ buckets), the adversarial ratio naturally decreases. The constraint means that for every ~2 non-adversarial fixtures added, ~1 adversarial fixture should be added to maintain the ratio. New adversarial fixtures should target the testing deserts identified in GOLDEN_CORPUS_COVERAGE_MAP.md (COMPLETENESS-004, FORMATTING-002, SECURITY-003).

**Enforcement:** The ratio is checked manually during the corpus review cycle. If the ratio drops below 30%, the review cycle must include adversarial fixture generation before any corrected pairs are merged into the corpus.


## Baseline Snapshot Protocol

Per DEFINITION_OF_DONE.md (Gate 1), regression testing requires a snapshot-based baseline. Each time the corpus is modified:

1. Record the current `golden_corpus_manifest.json` hash as the new baseline snapshot.
2. Tag the snapshot with the date and the roadmap item that was last completed against the previous baseline.
3. All subsequent roadmap items are tested against this new baseline until the corpus is modified again.

This ensures that "0% regression" is always measured against a specific, known corpus state rather than a moving target.


## Relationship to Other Artifacts

| Artifact | Relationship |
|----------|-------------|
| `golden_corpus_manifest.json` | The machine-checkable manifest. This SOP defines when and how entries are added to it. |
| `CORPUS_MANIFEST.md` | The human-readable companion. Updated in Step 4 of the action sequence. |
| `GOLDEN_CORPUS_COVERAGE_MAP.md` | Identifies testing deserts that should guide adversarial fixture generation when maintaining the 30% ratio. |
| `DEFINITION_OF_DONE.md` | Gate 1 (Logic) and Gate 2 (Security/Adversarial) depend on the corpus. This SOP ensures the corpus evolves without breaking the regression anchor. |
| `TELEMETRY_SPEC.md` | Corpus maintenance is not a telemetry event. It is a manual process triggered by ledger review. |
| Strategy Kit Roadmap Items 11-14 | The `provenance: "corrected_pair"` tag enables future DPO training to weight human-corrected examples appropriately. The ledger's full evaluation payloads (P0-14) provide the training signal; the corpus provides the regression baseline. |
