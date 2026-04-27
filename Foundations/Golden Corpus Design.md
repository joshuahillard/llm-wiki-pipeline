# Golden Corpus Design

## What This Page Is

This page explains the purpose and design of a golden corpus for an LLM evaluation pipeline. A golden corpus is a curated set of test fixtures with known expected outcomes. It exists so the system can be evaluated mechanically instead of by intuition alone.

For this project, the golden corpus is one of the most important control artifacts in the entire architecture. It converts abstract policy into concrete examples and gives the pipeline a repeatable way to test parser behavior, decision behavior, adversarial handling, and long-term regression risk.

## Why a Golden Corpus Matters

LLM systems are especially prone to hidden drift:

- prompts evolve
- schemas tighten
- model providers change
- policies are refined
- edge cases appear only after deployment

Without a golden corpus, teams often judge quality by anecdote:

- "it seemed fine on the last few articles"
- "the model usually catches obvious issues"
- "the new prompt feels better"

That is not enough for a governed system.

A golden corpus matters because it gives the project:

- deterministic expected outcomes
- regression detection
- calibration feedback
- adversarial hardening
- parity testing across model paths

It is one of the few tools that turns model behavior into something the team can reason about systematically.

For this project, the corpus is not just a useful collection. It is a logic and security gate for the implementation. Gate 1 of the Definition of Done depends on it for regression control, and Gate 2 depends on it for adversarial assurance.

## What Makes a Fixture Useful

A useful fixture is not merely a sample document. It is a sample designed to prove something specific.

A strong fixture should have:

- a clear purpose
- a stable expected result
- enough realism to exercise the actual system
- enough specificity that a failure is informative

Good fixture questions include:

- should this cleanly approve?
- should this clearly reject?
- should this escalate because the judgment is ambiguous?
- should this fail safely before the model is called?

Bad fixtures tend to be vague, overstuffed, or hard to interpret after a failure.

## Approve Fixtures

Approve fixtures prove that the system can recognize acceptable content and avoid unnecessary rejection.

They matter because many early LLM evaluators become too strict. A system that only rejects bad content but also rejects good content is not reliable. It simply fails in a more polished way.

Approve fixtures should test:

- clean well-formed articles
- minimal but valid articles
- long-form articles
- Unicode and formatting variety
- minor imperfections that should not block approval

Approve coverage helps define the lower bound of acceptable content quality without turning the system into a perfection engine.

## Reject Fixtures

Reject fixtures prove that the system can identify clear policy violations.

They matter because rejection logic is often where governance earns its credibility. If clearly bad content passes, the whole pipeline becomes harder to trust.

Reject fixtures should cover:

- factual contradictions
- outdated guidance
- placeholder content
- empty sections
- leaked credentials
- internal infrastructure details
- other policy violations that should deterministically block promotion

Reject fixtures should be specific enough that the correct decision is not debatable.

## Escalate Fixtures

Escalate fixtures prove that the system knows when not to force certainty.

This is a subtle but crucial capability. A pipeline that never escalates may look decisive, but it is often overconfident. In governance-heavy systems, uncertainty should be surfaced rather than hidden.

Escalate fixtures are useful for:

- ambiguous domain claims
- context-dependent tradeoffs
- borderline neutrality concerns
- claims that require specialist review

The goal is to teach the system that "I cannot safely decide" is a legitimate output, not a failure of intelligence.

## Adversarial Fixtures

Adversarial fixtures test whether the system fails safely under hostile or malformed conditions.

These are not ordinary quality cases. They are designed to challenge assumptions about:

- identity parsing
- frontmatter safety
- prompt injection
- oversized inputs
- malformed structure
- dangerous content

Adversarial coverage matters because the trust model must hold even when the input is trying to break it.

Examples:

- missing or malformed `source_id`
- invalid YAML
- UTF-8 BOM handling
- nested delimiters
- oversized frontmatter fields
- body-level injection attempts
- token overflow cases

This set should intentionally overrepresent dangerous edge cases early in the project.

For this project, "overrepresent" must be quantified. The corpus must maintain a minimum **30% adversarial ratio** at all times, consistent with `CORPUS_MAINTENANCE_SOP.md`.

That means:

- adversarial fixtures / total fixtures >= 30%
- growth that dilutes the adversarial subset below that floor is not allowed
- as a practical rule, every ~2 non-adversarial additions should be paired with ~1 adversarial addition when needed to preserve the floor

Without this floor, the harness can grow while becoming less protective.

## Integration Fixtures

Integration fixtures test behaviors that are larger than a single document decision.

Examples:

- context digest invalidation
- reconciliation behavior
- idempotent retries
- PR decline handling
- promotion equivalence checks
- manual promotion or corrected-pair paths

These fixtures are important because many serious failures do not happen inside a single evaluation. They happen at the seams between evaluation, orchestration, external state, and remote review state.

For this project, the T7 and T8 paths should be treated as first-class integration behavior:

- T7: declined PR -> `declined_by_human` state blocks re-promotion until `document_hash` or `context_digest` changes
- T8: human correction of a false rejection -> corrected-pair material for corpus growth and future training provenance

## How the Corpus Supports Calibration

The corpus is not only a pass/fail artifact. It is also a calibration tool.

Common signals:

- too many false rejects -> approve set is too weak or prompt is too strict
- too many false approves -> reject set is too weak or policy is underenforced
- no escalations -> ambiguity examples are not strong enough or prompt discourages uncertainty
- unstable results -> model path or prompt contract is underconstrained

This is why a corpus should evolve with the system. It should teach the system where its blind spots are becoming visible.

Calibration is not only about policy judgment. It is also about contract behavior. The corpus should include fixtures that stress logic-gate failures such as schema-invalid raw responses, taxonomy drift, and cross-field contradictions where applicable to the current validator contract.

## Coverage vs Confidence

A corpus can feel large while still being strategically thin.

Coverage asks:

- which rule categories are represented?
- which decision types are represented?
- which failure modes are represented?

Confidence asks:

- are there enough varied examples in each category to believe the results?
- do the fixtures test single issues and compound issues?
- are adversarial cases overrepresented enough to harden the system?

The right question is not "how many fixtures do we have?" It is "what decisions can we defend because of the fixtures we have?"

## Testing Deserts and Why They Matter

A testing desert is an area where the system has little or no meaningful fixture coverage.

This matters because an uncovered area can create false confidence. The system may seem stable only because it has never been forced to prove competence in that part of the policy space.

Common deserts to watch for:

- security rules with no direct examples
- formatting rules only tested indirectly
- neutrality rules covered only through escalation
- minor-violation approve cases
- article-type-specific completeness expectations

A mature corpus map should make these deserts visible rather than assuming they are harmless.

For this project, the current Priority 1-4 deserts identified in `GOLDEN_CORPUS_COVERAGE_MAP.md` are not passive observations. They are active testing debts:

- `NEUTRALITY-001`
- `FORMATTING-002`
- `SECURITY-003`
- `COMPLETENESS-004`

If a roadmap item materially touches one of these policy areas, that item must not be considered done until dedicated fixtures are added to close or meaningfully reduce the gap. A known desert is acceptable only when the current roadmap item does not claim competence in that category.

## How to Add New Fixtures

New fixtures should be added deliberately, not just whenever a new sample document is available.

A good workflow is:

1. identify a blind spot, regression, or real-world failure
2. decide whether the correct outcome is approve, reject, escalate, or safe fault
3. create a fixture that isolates the issue as cleanly as possible
4. record the expected outcome in the manifest
5. run the harness and confirm determinism
6. add a corrected pair when useful for before/after learning

This process keeps the corpus tied to learning and governance rather than turning it into a random collection of examples.

That fourth step should include more than content verdicts. Fixtures may also exist to force contract outcomes such as:

- `SCHEMA_FAULT`
- `SYSTEM_FAULT`
- `TOKEN_OVERFLOW`

The corpus is therefore responsible for covering both policy failures and logic-boundary failures.

## Corpus Maintenance Rules

A strong corpus needs maintenance discipline.

Mandatory maintenance rules:

- keep expected outcomes machine-readable
- preserve old fixtures unless they are truly obsolete
- add new fixtures when real failures or ambiguities appear
- maintain the adversarial floor rather than letting the set become too polite
- record a new baseline snapshot whenever the manifest changes
- document why each fixture exists

The corpus must behave like a strategic asset, not like temporary test data.

## Baseline Snapshot Protocol

For this project, baseline snapshots are not optional hygiene. They are the anchor for Gate 1 regression testing.

Each time `golden_corpus_manifest.json` changes:

1. record the new manifest content hash as the baseline snapshot
2. tie that snapshot to the roadmap item completed against the previous baseline
3. update `PROJECT_LEDGER.md` with the new baseline reference
4. treat future "0% regression" claims as measured against that exact snapshot until the corpus changes again

This protocol is mandatory for every manifest change. Without an immutable baseline anchor, the corpus becomes a moving target and regression claims lose meaning.

## Example Fixture Lifecycle

Imagine a real article is declined by a human reviewer after the model approved it. That event is valuable.

A healthy corpus process might do this:

1. sanitize the article
2. extract the decision-relevant pattern
3. add a failing fixture representing the original issue
4. add a corrected version showing the intended acceptable state
5. update the manifest and coverage notes

This turns production learning into reusable institutional knowledge.

If the event came from a T7 or T8 override path, that provenance should remain visible. Corrected-pair fixtures are more than extra samples; they are evidence that the system previously failed in a way a human had to repair.

## Hardened Category Requirements

The corpus categories should be treated as contract-bearing test classes, not just organizational buckets.

### Approve

Must prove that acceptable content can pass without false rejection.

### Reject

Must prove both policy rejection and contract-safe rejection behavior where applicable.

### Escalate

Must prove that ambiguity produces escalation rather than forced certainty.

### Adversarial

Must remain at or above the 30% floor and must cover parser, prompt, contract, and runtime stress cases.

### Integration

Must cover cross-component behaviors such as T7 decline handling, T8 corrected-pair learning, digest invalidation, and retry/reconciliation flows.

## Logic-Gate Fixtures

The corpus must not only test "bad content." It must also test "bad logic." This is a contract-integrity responsibility, not an optional enhancement.

Examples of logic-gate fixtures include:

- malformed raw model output that should produce `SCHEMA_FAULT`
- taxonomy-invalid rule IDs
- confidence values outside the schema contract
- cross-field contradictions such as a logically impossible approval payload
- critical-approval contradictions where `decision = approve` coexists with a `critical` violation
- token-overflow cases that must halt before provider invocation

These fixtures matter because a validator can fail safely or unsafely even when the underlying article content is unimportant. The corpus must therefore guard the contract boundary as well as the content policy boundary.

## Contract-Integrity Fixtures

Contract-integrity fixtures are a required corpus class. They exist to prove that deterministic control logic catches invalid model behavior even when the article content itself is not the primary issue.

At minimum, this class must cover:

- schema-invalid payloads
- taxonomy drift
- cross-field contradictions
- impossible severity-to-decision combinations
- token-budget enforcement paths

If the schema or governance contract gains a new mechanical rule, the corpus must gain fixtures that prove that rule is enforced.

## Design Tradeoffs

Golden corpus design comes with real tradeoffs:

### More realism

Benefits:

- better resemblance to production content
- stronger end-to-end relevance

Costs:

- harder debugging
- fixtures may bundle too many variables

### More isolation

Benefits:

- cleaner failure interpretation
- easier maintenance

Costs:

- less resemblance to messy real-world content

The best corpus usually mixes both:

- isolated fixtures for precise rule testing
- realistic fixtures for system-level behavior

## Review Checklist

Use this checklist when reviewing corpus quality:

- Does each fixture prove something specific?
- Are approve, reject, escalate, and adversarial paths all represented?
- Does the corpus maintain the 30% adversarial minimum floor?
- Are key policy categories directly covered?
- Are logic-gate failures covered, not just policy failures?
- Are integration behaviors tested somewhere?
- Are testing deserts documented explicitly?
- Are Priority 1-4 deserts being actively closed when roadmap work touches those areas?
- Can failures be interpreted quickly from the fixture design?
- Is the current baseline snapshot recorded and usable for Gate 1 regression claims?
- Is the corpus still aligned with current governance and schema contracts?

If these answers are weak, the corpus may be larger than it is useful.

## Related Pages

- `LLM System Trust Model`
- `Trust Boundaries in LLM Pipelines`
- `Schema Validation for LLM Output`
- `Policy Taxonomy and Severity Mapping`
- `Failure Modes and Recovery Paths`
