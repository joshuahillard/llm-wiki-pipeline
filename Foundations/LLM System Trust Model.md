# LLM System Trust Model

## What This Page Is

This page defines the trust model for an LLM-driven system. In this project, the trust model is the set of rules that determines what the system may accept, what it must verify, what it must reject, and where final authority lives. It is not only a security concept. It is also an architecture concept, an operations concept, and a governance concept.

For the LLM wiki architecture, this page is meant to answer a basic but important question:

**What parts of the system can be trusted as-is, and what parts must always be treated as untrusted until validated?**

If that question is answered clearly, the rest of the system becomes easier to design. If it is answered poorly, then even a technically impressive system can become unsafe, unauditable, or impossible to reason about.

## Why Trust Is the Core Problem in LLM Systems

Traditional software systems mostly operate on deterministic rules. If the same input goes into the same code path, the same output is generally expected. LLM systems are different. They can produce useful output, but they do not guarantee correctness, policy compliance, or even structural consistency. They are probabilistic systems wrapped inside deterministic software.

That means the central design problem is not only "how do we get the model to answer?" It is "how do we build a surrounding system that can safely use model output without confusing fluency for truth?"

In a wiki or knowledge system, this problem becomes more serious because the output may be treated as authoritative by future readers, future models, or automated workflows. Once bad content crosses the boundary into the verified knowledge base, it becomes harder to detect and more expensive to unwind.

The trust model exists to prevent that failure.

## Deterministic Components vs Non-Deterministic Components

A useful way to reason about an LLM system is to split it into deterministic and non-deterministic parts.

### Deterministic components

These are components that should behave the same way given the same inputs:

- file parsers
- schema validators
- hash generation
- transaction identity builders
- policy loaders
- ledger writers
- telemetry emitters
- branch and PR orchestration logic

These components form the control structure around the model. They are where reliability, auditability, and replayability come from.

### Non-deterministic components

These are components whose outputs may vary even when the inputs look similar:

- the LLM itself
- provider-specific inference behavior
- model fallback paths
- future ranking, routing, or ensemble logic

These components can assist judgment, but they should not be treated as self-certifying. Their outputs must be constrained and checked by deterministic layers before they influence state.

## Trusted Inputs, Untrusted Inputs, and Context-Locked State

Not everything in the system has the same trust level. A mature trust model distinguishes between categories of information.

### Trusted inputs

Trusted inputs are not "magically correct." They are simply inputs that come from controlled sources and can be verified mechanically. Examples include:

- checked-in policy files
- versioned schemas
- local orchestration code
- approved configuration manifests such as `validator_config.json`
- repository commit SHAs

These are trusted because they are versioned, reviewable, and deterministic.

### Untrusted inputs

Untrusted inputs are anything that can contain ambiguity, manipulation, malformed structure, or semantic error. Examples include:

- draft article content
- frontmatter fields before validation
- LLM responses
- API responses from external services
- manually edited content that has not yet passed policy checks

The key principle is simple: **untrusted does not mean useless. It means the system must validate before acting on it.**

For this project, that principle has several hard implications:

- `source_id` must match `^[a-zA-Z0-9-]{1,36}$`
- any identity-field deviation from that regex is a `SYSTEM_FAULT`, not a warning
- all frontmatter values are bounded to 256 bytes
- raw frontmatter is never passed to the LLM prompt unsanitized
- malformed frontmatter is not an evaluation problem; it is a control-plane rejection

This matters because identity is not ordinary content. Identity fields determine transaction keys, cache behavior, ledger writes, and promotion lineage. If identity is weak, every downstream control becomes weaker with it.

### Context-Locked state

Context-locked state sits in the middle. It is data produced by the system from a mix of trusted and untrusted inputs, but its trust only holds inside the exact control-plane context that created it. Examples include:

- transaction keys
- ledger entries
- evaluation summaries
- feedback sidecars
- cached approval states

Context-locked state becomes trustworthy only if the process that generated it is trustworthy and the surrounding runtime context has not changed. Trust is therefore **ephemeral**, not permanent. This is why deterministic validation layers and context digests matter so much.

## What "Trust-Nothing" Means in Practice

"Trust-nothing" does not mean the system assumes everything is hostile at all times. It means the system never grants authority without validation.

In practice, that means:

- the parser is the single authority for frontmatter identity
- identity parsing enforces the restricted `source_id` format and 256-byte bounds
- unsanitized raw frontmatter is never allowed to flow into prompt construction
- content is not promoted because it looks good; it is promoted only after policy evaluation and control-plane checks
- LLM output is never consumed directly without schema validation
- cached results are invalidated when the surrounding rules change
- external state is recorded so actions can be traced and reconciled later
- human reviewers retain merge authority over promoted content

This posture is especially important in AI systems because model output often appears coherent even when it is incorrect. A trust-nothing design refuses to let coherence substitute for evidence.

## Where Accountability Lives

A strong trust model is also an accountability model. It should be possible to answer:

- what content was evaluated
- which rules were active at the time
- which model configuration was used
- what the system decided
- whether the outcome was a governed decision or an operational fault
- what a human reviewer later did with that result

In this project, accountability should live in a chain of artifacts rather than in memory or informal explanation. That chain includes:

- the content file itself
- parser output
- transaction identity
- validation result
- append-only telemetry events
- ledger entries
- PR state
- human merge or decline outcome

If one of these links is missing, the system becomes harder to defend. It may still function, but it is no longer a strong source of truth.

## Human Authority vs Model Authority

One of the easiest mistakes in LLM architecture is to give the model too much implied authority.

The model should have limited authority:

- classify content against defined policy
- produce a structured decision
- recommend approve, reject, or escalate

The model should not have final authority:

- it should not write directly into the verified corpus
- it should not merge PRs
- it should not define policy
- it should not override the governance boundary

Human reviewers hold final publication authority. This is not just a safety feature. It is what makes the system governable. A model recommendation is part of the review process, not the end of the review process.

In this architecture, that authority is enforced mechanically through protected-branch settings and PR-gated promotion. The pipeline may propose a promotion candidate, but it does not gain the authority to merge it. Branch protection is therefore part of the trust model, not just a repository convenience.

For this project, model authority is strictly bound to the decision contract:

- exit code `0` = `APPROVE`
- exit code `1` = `REJECT`
- exit code `2` = `ESCALATE`

The model does not define any other successful outcome. Exit codes `3`, `4`, and `5` are fault paths owned by the control plane, not alternative model verdicts.

## How Trust Relates to Security, Validation, and Auditability

These three ideas are closely related but not identical.

### Security

Security asks whether the system prevents harmful or unauthorized outcomes. In this project, that includes preventing sensitive content, prompt injection through identity fields, bad promotion paths, and state corruption.

### Validation

Validation asks whether inputs and outputs satisfy the contracts required by the system. For example:

- does frontmatter contain a valid `source_id`
- does model output match the schema
- does a file fit within token limits
- does a PR correspond to the intended tree state

### Auditability

Auditability asks whether someone can reconstruct what happened after the fact. It is the reason transaction keys, logs, and ledger state matter. Without auditability, the system may still reject bad content, but it cannot prove why it acted the way it did.

For this project, telemetry integrity is part of auditability. The telemetry stream should be append-only during a run so the operational record is itself a trusted deterministic artifact rather than an editable narrative of what happened.

Together, security, validation, and auditability are what turn an LLM feature into a trustworthy system.

## Context Digest and Trust Invalidation

Trust in this system is locked to a runtime context digest. A prior approval is only trustworthy if it was produced under the same control-plane and model context that is active now.

That digest should include the material components of the control plane, including:

- parser logic
- validator logic
- orchestration logic
- promotion logic
- `validation_result.schema.json`
- the policy bundle
- the base repository state
- `validator_config.json`

For the model configuration manifest, trust must rotate when any digest-contributing field changes. In the current design that means 8 of the 9 fields in `validator_config.json` affect trust invalidation:

- `provider`
- `model_id`
- `quantization_level`
- `temperature`
- `top_p`
- `max_context_tokens`
- `system_instruction_hash`
- `lora_adapter_path`

`tokenizer_id` is excluded from the digest because it is derived from `model_id`, but it still matters operationally for budget calculation.

This rule is intentionally strict. A change to `temperature`, `top_p`, or `model_id` is not a cosmetic change. It changes the evaluation environment and therefore invalidates prior trust.

## Decision Outcomes vs Fault Outcomes

The trust model should distinguish sharply between decisions and faults.

### Decision outcomes

These are governed content outcomes:

- exit code `0` = approve
- exit code `1` = reject
- exit code `2` = escalate

These outcomes are eligible for ledger writes because they represent a completed evaluation.

### Fault outcomes

These are control-plane failures:

- exit code `3` = schema fault
- exit code `4` = system fault
- exit code `5` = token overflow

These outcomes are not governed decisions about the article. They are failures of the pipeline to safely complete evaluation under the required contract. They should emit telemetry and preserve conservative state, but they should not be confused with content verdicts.

This distinction is critical because a malformed model response is not a rejection, and an oversized article is not an escalation. Faults and decisions must remain mechanically separate.

## Conservatism as a Mechanical Rule

The project describes itself as conservative, but conservatism should not remain only a design attitude. It should be implemented as a mechanical rule.

In practice, that means:

- clear critical violations force rejection
- ambiguity forces escalation rather than approval-by-default
- three or more minor violations should trigger escalation rather than a casual approve-with-notes outcome
- overlapping policy signals or unresolved context dependence should route to exit code `2`
- confidence weakness should not be hidden behind forced binary outcomes

Exit code `2` should therefore be understood as a fail-safe. It exists so the system can preserve trust when the evaluation boundary is not strong enough to justify a definitive approve or reject.

## Fallback Paths and Recorded Trust

Trust is not preserved automatically when evaluation falls back from one model path to another.

If a self-hosted path fails and the system re-runs evaluation using a managed model path, that fallback must be treated as a new evaluation context, not as a transparent continuation of the old one.

That means:

- a new evaluation is produced under the managed config
- the managed path is recorded in the ledger
- the fallback source and reason are retained
- trust attaches to the new evaluation, not the failed one

This matters because the pipeline is hybrid by design. Trust must survive provider diversity without becoming vague about which model path actually produced the decision.

## Example Trust Model for the LLM Wiki

The table below shows a practical trust breakdown for this project.

| Component | Deterministic | Trusted As-Is | Validation Required | Reason |
| --- | --- | --- | --- | --- |
| `parse_identity.py` | Yes | Yes, if version-controlled | Yes, on its outputs at boundaries | Canonical parser for identity extraction |
| Draft markdown in `provisional/` | No | No | Yes | Human- or AI-authored content may be wrong or malformed |
| Frontmatter before parsing | No | No | Yes | Identity data can be malformed or adversarial; unsanitized values must not reach the prompt |
| LLM raw response | No | No | Yes | Fluent output is not reliable output |
| `validation_result.schema.json` | Yes | Yes | Yes, as system contract | Governs allowed structure and distinguishes valid decisions from schema faults |
| `validator_config.json` | Yes | Yes | Yes, as context authority | 8 of 9 fields rotate trust by changing the context digest |
| Transaction key | Yes | Conditionally | Yes | Only trustworthy if built from validated inputs |
| Telemetry logs | Yes | Conditionally | Yes | Trust depends on correct emission and append-only handling |
| Ledger entry | Yes | Conditionally | Yes | Trust depends on complete and correct write path |
| PR merge outcome | Yes | Yes | Yes, for reconciliation | Final human decision must be recorded accurately |

This table shows the core pattern of the system:

- **content is untrusted**
- **control logic is deterministic**
- **trust is earned through validation**

## Common Mistakes in Trust Design

Several failure patterns appear again and again in LLM systems:

### 1. Treating model output as if it were already validated

This is the fastest way to lose control of the system. A model may emit malformed JSON, unsupported fields, or a structurally valid but logically weak result.

### 2. Splitting authority across multiple parsers

If one component parses identity differently from another, the system can create mismatched state. This causes collisions, broken audit trails, and hard-to-debug reconciliation problems.

### 3. Using weak cache keys

If cache identity only tracks file bytes and ignores context, the system may silently trust stale evaluations even after policy or code changes.

### 4. Treating fallback as if it were the same evaluation

If a failed self-hosted evaluation transparently becomes a managed one without explicit recording, the system loses provenance and weakens auditability.

### 5. Letting automation bypass human governance

A system that auto-publishes without an explicit human boundary may scale faster, but it becomes much harder to defend when something goes wrong.

### 6. Logging too little

If the system only stores approve or reject outcomes without the surrounding context, it loses both forensic value and future training value.

## Training Integrity

This project has an explicit "log now, build later" architecture decision. That means trust in future model adaptation depends on the quality and provenance of the ledger data captured today.

At minimum, the system should retain the following fields for decision outcomes:

1. transaction key
2. full model output
3. model configuration snapshot
4. decision
5. timestamp
6. model path
7. reviewer outcome

This is not optional bookkeeping. It is part of the trust model.

If those fields are incomplete, then future DPO, LoRA, or other adaptation workflows will be built on partial or ambiguous evidence. That would weaken trust in later model iterations before they are even trained.

Trust in future models therefore begins with ledger integrity in the present system.

## Design Principles to Keep

For this project, the trust model should stay anchored to a few durable principles:

1. Treat all model output as untrusted until validated.
2. Keep identity extraction under one canonical parser.
3. Make transaction identity stable, explicit, and traceable.
4. Treat trust as context-locked and invalidate it when runtime conditions change.
5. Keep decision outcomes distinct from operational faults.
6. Store enough state to reconstruct any important decision and future training provenance.
7. Preserve a human publication boundary.
8. Prefer deterministic failure over silent ambiguity.

These principles should be visible not only in docs, but in file layout, runtime contracts, telemetry, and tests.

## A Working Definition of Source of Truth

In this system, a source of truth is not a single file. It is a controlled set of authoritative artifacts that define how the system should behave and how its actions can be verified.

For the LLM wiki, that source of truth should include:

- policy definitions
- validation schema
- parser rules
- transaction identity rules
- ledger and telemetry contracts
- human review outcomes

The wiki itself can document these things, but the runtime system must also embody them. A page is only a true source of truth if the implementation and tests reinforce what the page says.

## Checklist

Use this checklist when reviewing any new component in the system:

- Does it operate on trusted or untrusted input?
- If untrusted, where is validation performed?
- If it touches identity, does it enforce the exact parser constraints?
- Is its output deterministic or probabilistic?
- If probabilistic, what deterministic layer constrains it?
- Does it create or modify durable state?
- Can that state be traced back to a transaction key?
- Is that state locked to the active context digest?
- Does it distinguish decision outcomes from fault outcomes?
- If the rules change, does prior trust get invalidated?
- If a fallback path occurs, is the new provenance recorded explicitly?
- Does a human still control final publication?

If these questions cannot be answered clearly, the component is probably underdesigned.

## Related Pages

- `Trust Boundaries in LLM Pipelines`
- `Transaction Identity and Auditability`
- `Schema Validation for LLM Output`
- `Golden Corpus Design`
- `Human-in-the-Loop Governance`
- `Program Management for Technical Infrastructure`
