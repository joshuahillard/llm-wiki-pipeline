# Program Management for Technical Infrastructure

## What This Page Is

This page explains how program management applies to technical infrastructure work, especially work that is architecture-heavy, cross-functional, and not immediately visible to end users.

For this project, program management is not an administrative layer placed on top of engineering. It is part of how the architecture becomes real. It provides the planning structure, sequencing logic, risk tracking, and delivery discipline needed to turn a strong design into a working system.

For the LLM-Wiki project, this page is also a delivery contract. It defines how roadmap items are allowed to move from planned to complete, what evidence counts, when sequencing must stop for safety work, and how implementation drift is prevented.

## Why PM Matters for Infrastructure Work

Infrastructure projects often fail in one of two ways:

- they stay trapped in design forever
- they ship pieces of code without proving that the system as a whole is becoming safer, clearer, or more operable

Program management helps avoid both failures.

In infrastructure work, PM is especially important because:

- the work has many dependencies
- quality is often invisible until something breaks
- multiple stakeholders care for different reasons
- partial implementation can create false confidence
- risk reduction is often more important than feature count

In a project like this one, PM is how you make sure the implementation path preserves the architecture's intent.

## Turning Architecture into Deliverables

Architecture documents answer:

- what the system should be
- why certain tradeoffs were chosen
- what constraints must be preserved

Program management answers:

- what gets built first
- how progress is measured
- how risk is surfaced early
- when a milestone is actually complete

This translation from architecture to deliverables is where many technical projects become real or stall out.

A good PM lens asks:

- what is the smallest vertical slice that proves the architecture?
- what work is foundational and what work is optional?
- what is blocked by external decisions?
- what evidence should exist before calling something done?

For this project, that last question has a strict answer: a roadmap item is done only when it is gate-verified under [DEFINITION_OF_DONE.md](../strategy/DEFINITION_OF_DONE.md).

## PRDs, ADRs, and Roadmaps

Three planning artifacts are especially useful in infrastructure work.

### PRD

The product requirements document explains:

- the problem
- the goals
- the non-goals
- the users
- the success metrics

In technical infrastructure, the "product" is often an internal capability rather than a visible UI. That does not make the PRD less useful. It makes it more important.

### ADR

The architecture decision record explains:

- what decision was made
- what alternatives were considered
- why the choice was made
- what tradeoffs came with it

ADRs matter because infrastructure choices accumulate. If those choices are not recorded, later contributors may undo them casually or fail to understand why the system looks the way it does.

### Roadmap

The roadmap sequences work over time.

It should make dependencies visible:

- parser before runner
- runner before orchestration
- orchestration before promotion
- telemetry and ledger before operational maturity claims

The roadmap is where architecture becomes execution order.

For this project, sequencing is not only dependency-aware. It is also coverage-aware. A component that claims competence in a policy area may not be considered complete while that area remains a Priority 1-4 testing desert.

## Defining Scope and Non-Goals

One of the most useful PM skills in technical projects is being able to say:

- what this phase will do
- what this phase will not do
- what is intentionally deferred

Without that discipline, infrastructure projects expand in all directions:

- too many integrations
- premature optimization
- too many provider paths
- too many polish features before the control plane is stable

For this project, examples of strong non-goal thinking include:

- not building content generation into the validation pipeline
- not requiring multi-model consensus in v1
- not forcing cross-platform portability before the Windows-first control plane works

Non-goals protect momentum.

## Sequencing Dependencies

Good sequencing is one of the clearest signs of mature program management.

Not all work has the same dependency structure. Some tasks unlock many others, while some tasks are valuable but non-blocking.

For this project, an effective early sequence looks like:

1. canonical parser
2. schema contract
3. validator runner with structured output handling
4. token budget gate
5. telemetry and ledger writes
6. orchestration
7. promotion workflow
8. parity harness and later optimization

Why this matters:

- it proves the core trust path before expanding features
- it avoids building promotion logic on top of an unstable evaluator
- it reduces the chance of beautiful architecture with no executable center

### Desert-Gated Sequencing

Sequencing must also account for testing debt identified in [GOLDEN_CORPUS_COVERAGE_MAP.md](../strategy/GOLDEN_CORPUS_COVERAGE_MAP.md).

Required rule:

- if a roadmap item materially claims competence in a Priority 1-4 desert category, that item must not be marked complete until dedicated fixtures are added to close or meaningfully reduce the gap

This matters especially for `validator_runner.py`, because it is the first component that turns policy competence into executable behavior. The runner is not done merely because it executes; it is done when the corpus proves its behavior in the categories it claims to handle.

## Risk Management and FMEA Thinking

Infrastructure PM is heavily tied to risk management.

A feature-oriented mindset asks:

- what can we build next?

A systems-oriented PM mindset also asks:

- what can fail next?
- where is the highest leverage risk reduction?
- what failure would be expensive to discover late?

This is where FMEA-style thinking helps. It forces the project to consider:

- failure mode
- cause
- effect
- detectability
- mitigation

That style of thinking is especially useful for AI infrastructure because failures are often subtle until they become expensive.

For this project, FMEA thinking must not remain conceptual. Each roadmap item must identify which failure modes it mitigates and must produce reviewable evidence that those mitigations were exercised. A mitigation that is not tested against its assigned failure mode is not complete.

## Definition of Done for Infrastructure

One of the biggest PM mistakes in technical work is defining done as "code exists."

For the LLM-Wiki project, "done" is not a matter of judgment. It is a gated state.

### Gate-Verified Completion

No roadmap item may be marked complete in the sprint tracker until it passes all seven quality gates in [DEFINITION_OF_DONE.md](../strategy/DEFINITION_OF_DONE.md), with evidence recorded in [PROJECT_LEDGER.md](../PROJECT_LEDGER.md).

The required evidence model includes:

- Gate 1 logic results against the current corpus baseline
- Gate 2 adversarial results against the full adversarial subset
- Gate 3 identity integrity review
- Gate 4 telemetry evidence from pipeline logs
- Gate 5 boundary and contract verification
- Gate 6 ledger and audit evidence
- Gate 7 documentation and ledger update evidence

This is why quality gates matter. They turn "we implemented it" into "this roadmap item is trustworthy enough to build on."

## Measuring Progress Beyond "Code Written"

Useful progress metrics for infrastructure are often indirect.

Examples:

- number of critical invariants now enforced
- number of deterministic tests passing
- number of failure modes covered
- number of operational events now observable
- percentage of workflow that is replayable and auditable

These are stronger indicators than raw file count or line count because they measure system maturity rather than activity.

For this project, progress must also be baseline-anchored. Gate 1 claims are measured against the current `golden_corpus_manifest.json` snapshot hash, not against memory or informal expectations.

### SLI Breach Protocol

SLIs are not passive dashboard numbers. They are governance signals.

If either of the following occurs, the program must stop feature expansion and prioritize corrective work:

- SLI-2 PR Success Rate falls below the target defined in [TELEMETRY_SPEC.md](../strategy/TELEMETRY_SPEC.md)
- SLI-3 Fault Rate rises above the target defined in [TELEMETRY_SPEC.md](../strategy/TELEMETRY_SPEC.md)

In this project, a sustained SLI breach means the trust path is degraded. New roadmap features must not outrank restoring controlled operation.

## Stakeholder Communication

Infrastructure projects usually have more than one audience:

- engineering wants clear contracts and maintainable sequencing
- product wants confidence that the work maps to business value
- operations wants reliability and operability
- reviewers want traceability and risk control

Good PM makes the same project legible to all of them without flattening the technical detail.

A helpful practice is to map each major capability to:

- user or stakeholder value
- architectural purpose
- operational evidence

That makes it easier to explain why a parser, schema, or ledger matters even when it does not look like a traditional feature.

For this project, stakeholder value should also be audit-traceable. A mature milestone should make it possible to trace any `verified/` article back to its validation and governance record quickly and deterministically.

## Good Sprint Design for This Project

A good sprint for this project should aim to produce a completed control slice, not scattered partials.

Examples of good sprint goals:

- "one draft can be parsed, evaluated, schema-validated, and logged deterministically"
- "approved content can enter a traceable promotion path with no duplicate state"
- "all exit code paths are observable and handled correctly"

Examples of weak sprint goals:

- "start provider integration"
- "improve architecture docs"
- "add more infrastructure support"

Strong sprint goals produce evidence. Weak sprint goals produce motion without closure.

For this project, sprint goals should also name the gate evidence expected at the end of the sprint. A sprint that cannot state its expected gate artifacts is under-specified.

## What to Ship First

The first thing to ship should not be the broadest capability. It should be the most educational and structurally important capability.

For this project, that means proving the core trust loop:

- canonical identity
- structured evaluation
- schema validation
- transaction key creation
- telemetry emission
- ledger write

Once that loop is real, the rest of the system has something solid to wrap around.

That first shipped loop should also be digest-aware. If a change materially affects evaluation behavior, the same delivery unit must update the context-digest inputs that govern cache invalidation and re-evaluation.

## Common PM Failure Modes in Technical Projects

Some common failure patterns:

### 1. Overbuilding before proving the core

The team designs for every future possibility before validating the central loop.

### 2. Confusing progress with expansion

Adding folders, integrations, or docs can feel like momentum even when the main path is still incomplete.

### 3. Shipping without an evidence model

If there is no clear proof that a milestone works, the project accumulates optimism debt.

### 4. Underweighting operational readiness

Telemetry, logs, and reconciliation are often delayed because they are less exciting. In governed systems, that is a mistake.

### 5. Letting architecture and implementation drift apart

A design can stay elegant on paper while the codebase gradually stops reflecting it.

For this project, the most dangerous drift is digest drift: evaluation behavior changes in code or configuration, but the context digest logic is not updated to invalidate prior results.

### 6. Treating SLIs as reporting instead of control

In a governed system, bad metrics are not only interesting. They are instructions to stop and repair.

## Digest-Locked Implementation

Any change that materially affects evaluation behavior must be delivered with its corresponding digest impact in the same PR or change set.

Examples include changes to:

- evaluation scripts
- schema contract
- policy bundle
- model configuration fields that participate in trust invalidation
- promotion or reconciliation logic that changes decision meaning

If the implementation changes but the digest logic does not, the project has created a hidden trust bug. Program management must treat that as incomplete work, not as follow-up polish.

## A Practical Review Checklist

Use this checklist when reviewing project planning:

- Is the current milestone tied to a core architectural risk?
- Does the roadmap sequence dependencies logically?
- Are non-goals protecting focus?
- Is there evidence for calling the milestone done?
- Is the milestone fully gate-verified rather than informally "working"?
- Are baseline snapshot hashes and ledger references recorded?
- Are testing deserts blocking any claimed competence?
- Are assigned FMEA mitigations actually exercised by evidence?
- Are current SLI targets being met, or has the program stopped the line?
- Did every material evaluation change update digest logic in the same delivery unit?
- Are risks and failure modes visible, not implied?
- Is progress being measured in system maturity, not just activity?
- Can engineering, product, and operations each explain why this milestone matters?

If not, the project may be moving, but not necessarily advancing.

## Related Pages

- `LLM System Trust Model`
- `Trust Boundaries in LLM Pipelines`
- `Transaction Identity and Auditability`
- `Golden Corpus Design`
- `Architecture Decision Records`
- `Roadmaps, Dependencies, and Sequencing`
