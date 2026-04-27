# Trust Boundaries in LLM Pipelines

## What This Page Is

This page explains the major trust boundaries in an LLM pipeline and why they matter. A trust boundary is a point in the system where information crosses from one reliability level to another and must be checked before the system continues.

For this project, trust boundaries are the places where a draft, identity field, model response, or external system state could introduce error, ambiguity, or risk. If those boundaries are not designed carefully, the pipeline may still appear to work while quietly allowing bad decisions into durable state.

This page is meant to answer a practical question:

**Where should the system stop, validate, and decide whether it is safe to continue?**

## What a Trust Boundary Is

A trust boundary is not just a network edge or a permissions edge. In an LLM system, it is any handoff where the system is about to let one component influence another component that has more authority or more permanence.

Examples:

- a markdown file moving into the parser
- parsed metadata being accepted as identity
- article content being assembled into a model prompt
- model output being accepted as structured evaluation
- an approval result being allowed to affect promotion state
- a PR outcome being written back into the ledger

Each of these moments creates a design question:

**What assumptions are we making at this boundary, and how do we prove they are safe enough?**

## Why LLM Pipelines Need Multiple Trust Boundaries

It is tempting to think of the model as the main source of uncertainty. In reality, uncertainty enters the system in several places:

- content can be malformed
- identity fields can be adversarial
- prompts can be assembled incorrectly
- model responses can be syntactically invalid
- external APIs can return stale or unexpected state
- cached approvals can outlive the rules that created them

This is why a single validation step at the end is not enough. A trustworthy pipeline uses many narrow boundaries instead of one broad assumption. Each boundary reduces the blast radius of error.

The design goal is not to eliminate all uncertainty. The goal is to localize it, constrain it, and prevent it from silently gaining authority.

## Boundary 1: Content Ingestion

The first trust boundary is when draft content enters the pipeline.

At this point, the system should assume:

- the content may be incomplete
- the formatting may be broken
- the frontmatter may be missing or malformed
- the content may contain sensitive data
- the content may include prompt injection attempts

This means ingestion should not grant trust. It should only grant admission into the evaluation path.

What should be validated here:

- file existence
- expected location under `provisional/`
- readable encoding
- basic size and processing constraints

What should not happen here:

- implicit promotion decisions
- local parsing shortcuts that bypass canonical logic
- writing durable approval state before evaluation

The ingestion boundary is where the system first acknowledges the content, not where it believes the content.

## Boundary 2: Identity Extraction

Identity extraction is one of the most important trust boundaries in the system because identity controls auditability, caching, lineage, and promotion semantics.

In this project, the identity boundary should be owned by one canonical parser. The reason is simple: if multiple components derive identity in different ways, then the system no longer has one reality. It has competing realities.

What should be validated here:

- frontmatter exists at the beginning of the file
- YAML parses correctly
- required identity fields are present
- `source_id` follows the allowed format
- frontmatter values are bounded and sanitized

What the output of this boundary should become:

- a structured identity object
- not a free-form string
- not a partial best guess
- not something reconstructed separately by downstream components

This boundary is a hard gate. It must trigger exit code `4` (`SYSTEM_FAULT`) if:

- `source_id` deviates from `^[a-zA-Z0-9-]{1,36}$`
- the frontmatter is malformed
- the required identity fields are missing
- identity data cannot be trusted enough to construct a canonical transaction key

The current project contract is intentionally asymmetric here:

- identity fields fail closed
- non-identity frontmatter values may be bounded and sanitized to the enforced byte limit

That bounded sanitization is the only permitted degradation at this boundary, and it only applies to non-identity fields. No overlong or malformed identity value may enter the transaction key, and no raw unsanitized frontmatter value may flow into prompt construction.

This boundary is where the system decides whether it has enough trustworthy identity information to continue.

## Boundary 3: Prompt Construction

Prompt construction is a trust boundary because it transforms validated and unvalidated inputs into the exact material the model will see.

Even if the parser succeeds, the article body is still untrusted content. The system must avoid letting that content distort the control instructions or blur the distinction between policy and subject matter.

What should be controlled here:

- system instructions come from trusted versioned artifacts
- policy text comes from trusted versioned artifacts
- article metadata is serialized safely
- article content is inserted as data, not as authority
- token budget is checked before sending the request

This token-budget gate must use the active model's tokenizer contract, as defined by the current `tokenizer_id` and `max_context_tokens` in `validator_config.json`. If the total request size exceeds `max_context_tokens` minus the reserved headroom required by the runtime contract, the system must trigger exit code `5` (`TOKEN_OVERFLOW`) and halt evaluation for that file before any provider call is made.

The tokenizer contract must also remain configuration-locked. If the active tokenizer selection is inconsistent with the configured model path, the system should halt with exit code `4` (`SYSTEM_FAULT`) rather than continue under ambiguous budgeting assumptions.

Important design principle:

**Prompt construction must preserve role separation.**

The model should be able to distinguish:

- system rules
- policy criteria
- metadata
- article body

If these layers are mixed loosely, the system creates opportunities for injection, misinterpretation, and unstable evaluation behavior.

## Boundary 4: LLM Output Reception

When the model returns a response, the system reaches another major trust boundary.

At this point, the output may be:

- well-formed and useful
- malformed JSON
- structurally valid but semantically weak
- missing required fields
- overconfident but wrong
- wrapped in markdown fences or extra explanation

The key mistake at this boundary is assuming that because the model responded, the response is ready to use.

It is not ready yet.

The system should treat raw model output as untrusted text until proven otherwise.

At this boundary, the correct next step is not decision routing. The correct next step is contract verification.

## Boundary 4.5: Model Path Integrity

In a hybrid deployment model, the inference environment is itself a trust boundary. A response is not trustworthy merely because it arrived. It must also come from the model path the control plane intended to use.

This boundary should verify:

- the active provider path matches the current configuration
- the reported `model_id` matches the configured `model_id`
- the reported quantization or adapter state is consistent with the configured runtime
- fallback behavior, if any, is explicitly recorded as a new evaluation context

Any mismatch between the configured model path and the effective inference path should trigger exit code `4` (`SYSTEM_FAULT`). In a stricter future implementation, this boundary should also emit an explicit model-path integrity fault event.

## Boundary 5: Schema Validation

Schema validation is the formal gate that turns raw model output into structured system input.

This boundary is where the pipeline should verify:

- required fields exist
- decision values are allowed
- confidence is in range
- policy violation objects match the contract
- unexpected fields are rejected

This boundary matters because it prevents the model from inventing its own interface.

Without schema validation, the model effectively controls the downstream contract. With schema validation, the software controls the contract and the model must conform to it.

It is also important to remember what this boundary does **not** prove:

- it does not prove factual correctness
- it does not prove policy quality
- it does not prove the decision is wise

It only proves that the response is structurally safe to process further.

If the response fails validation against `validation_result.schema.json`, the system must trigger exit code `3` (`SCHEMA_FAULT`), emit an `operational_fault` telemetry event, and prohibit downstream actions such as promotion-branch creation or decision-state ledger writes.

At this boundary, the schema is the law. Unknown field names, missing required fields, invalid enum values, or invalid nested structures are not advisory defects. They are contract failures.

## Boundary 6: Decision-to-State Transition

Once the system has a valid structured result, it reaches the next trust boundary: deciding whether that result is allowed to affect durable state.

This includes actions such as:

- writing a ledger entry
- creating a feedback sidecar
- emitting evaluation telemetry
- placing an article in the promotion queue

What should be true before this boundary is crossed:

- identity is canonical
- transaction key is stable
- schema validation passed
- exit code mapping is deterministic
- the system knows whether the result is approve, reject, escalate, or fault

This is the boundary where the pipeline must separate governed outcomes from control-plane failures:

- exit codes `0-2` are decision outcomes and may update decision state
- exit codes `3-5` are fault outcomes and must not be treated as content verdicts

This boundary is especially important because it determines what becomes part of the system's memory. If state is written too early or too loosely, later reconciliation becomes unreliable.

This boundary must also behave as a write-ahead durability gate. The system should treat `evaluation_completed` telemetry emission and decision-state ledger persistence as one logical transaction that completes before promotion initialization begins. If durable decision recording fails, the system must not proceed into promotion.

## Boundary 7: Promotion / Publication

Promotion is the highest-risk trust boundary because it moves a piece of content closer to canonical status.

Even after evaluation succeeds, the system should remain conservative here. Promotion logic should verify:

- the source file is still the intended file
- the target path preserves namespace
- the staged change set matches intent
- the remote PR state is consistent with local expectations
- retries do not create duplicate branches or duplicate PRs

This boundary must fail closed. If namespace preservation, transaction identity, or remote equivalence checks fail, promotion must halt with conservative state preservation. A tree-SHA mismatch or equivalent remote-state integrity failure is a `SYSTEM_FAULT`, not a soft warning.

For promotion, "fail closed" means more than "stop." It means the pipeline should actively erase partial promotion state where possible:

- delete the ephemeral local branch
- close or avoid creating the remote PR when the intent is no longer trustworthy
- revert local `verified/` moves or staging changes
- preserve conservative ledger state rather than recording a false success

Tree-SHA mismatch should be treated as tamper-detection-grade failure. In a stricter telemetry implementation, it should also emit an explicit audit-alert-style event in addition to the `SYSTEM_FAULT` handling path.

This is where control-plane integrity matters most. The system is no longer only evaluating text. It is modifying review state and preparing content for publication.

If this boundary is weak, even a good evaluator can feed a bad publication process.

## Boundary 8: External State and Audit Storage

A less obvious trust boundary exists when the pipeline writes operational state outside the content repository.

This includes:

- telemetry logs
- ledger entries
- audit records
- reconciliation metadata

This boundary matters because external state becomes the long-term memory of the system. It is used to answer questions later:

- was this file already evaluated
- under what rules was it evaluated
- did a human decline this PR
- should the system retry or skip

What should be protected here:

- append-only or carefully controlled write behavior
- stable transaction identity
- immediate persistence after critical transitions
- clean separation from content files

If external state is sloppy, the system may appear correct in the moment but become untrustworthy over time.

## Boundary 9: Human Review and Final Authority

The final trust boundary is the handoff from automation to human authority.

This boundary exists because approval by the model is not the same thing as publication approval. The system may recommend action, but a human reviewer should decide whether content enters the verified corpus.

This boundary should preserve:

- visibility into why the model decided what it decided
- the ability to merge or decline independently
- clear recording of the human outcome
- rules for when declined content re-enters the queue

In this architecture, human authority is enforced mechanically by protected branches and PR-gated promotion. The pipeline's authority ends at PR creation. If a human reviewer declines a PR (`state=closed`, `merged=false`), the system must record the `declined_by_human` state and block re-promotion until either the document hash changes or the context digest changes.

That decline is effectively hash-locked. The system must not reinterpret the same content under the same context as newly promotable simply because a later run occurred.

This is the governance boundary of the whole system. If it disappears, then the system stops being a review pipeline and starts being an auto-publishing machine.

## Boundary Failures and What Happens When They Break

A useful trust-boundary design does not only define success. It also defines failure behavior.

Examples:

- if ingestion fails, the file should not enter evaluation
- if identity extraction fails, no transaction key should be created and the file should terminate with exit code `4`
- if token budget fails, no API call should be made and the file should terminate with exit code `5`
- if schema validation fails, no promotion path should be opened and the file should terminate with exit code `3`
- if promotion reconciliation fails, durable state should remain conservative and the boundary should terminate with exit code `4`
- if human review declines a PR, the system should respect that decline until meaningful change occurs

This is why boundaries should fail in explicit ways. Silent continuation is usually the most dangerous outcome because it allows uncertainty to accumulate.

## Fail Closed vs Fail Open

One of the most important choices at any trust boundary is whether the system should fail closed or fail open.

### Fail closed

Fail closed means the system stops when validation is not good enough.

Examples:

- invalid `source_id`
- malformed YAML
- schema-invalid model output
- token overflow
- tree mismatch during promotion

This is the right default for boundaries that protect identity, state integrity, or publication.

### Fail open

Fail open means the system continues despite uncertainty.

This may be acceptable only in narrow cases, such as:

- truncating a non-identity frontmatter field
- logging an informational observation without blocking approval
- allowing a retriable infrastructure fault to be picked up in a later run

The general rule for this project should be:

**fail closed on identity, contract, promotion, and publication boundaries; fail open only where the risk is bounded, explicitly intentional, and does not weaken transaction identity or policy enforcement.**

No fail-open behavior is permitted for:

- identity construction
- model-path integrity
- schema compliance
- token-budget enforcement
- promotion equivalence checks
- human decline handling

## Example Boundary Map for This Project

The following flow shows the major boundary sequence in the LLM wiki pipeline:

1. Draft file appears in `provisional/`
2. Canonical parser validates frontmatter and emits identity
3. Prompt builder assembles policy plus article payload
4. Token budget gate decides whether evaluation is even allowed
5. Model returns raw response
6. Schema validator checks the response contract
7. Decision is mapped into structured state
8. Ledger and telemetry are written
9. Approved content enters PR-based promotion flow
10. Human reviewer merges or declines
11. Reviewer outcome becomes part of the audit trail

Each step is a handoff. Each handoff should answer the same question:

**What exactly are we trusting now that we were not trusting one step earlier?**

## Boundary-to-Exit-Code Mapping

The trust boundaries in this system should resolve into the explicit runtime contract rather than vague failure language.

| Boundary | Failure Trigger | Exit Code | Effect |
| --- | --- | --- | --- |
| Identity Extraction | Invalid `source_id`, malformed YAML, missing required identity fields | `4` (`SYSTEM_FAULT`) | No transaction key, no evaluation |
| Prompt Construction | Token budget exceeds active model context window | `5` (`TOKEN_OVERFLOW`) | No provider call, file skipped conservatively |
| Model Path Integrity | Effective provider/model runtime does not match configured path | `4` (`SYSTEM_FAULT`) | Evaluation outcome is not trusted; no decision-state transition |
| Schema Validation | Response fails `validation_result.schema.json` | `3` (`SCHEMA_FAULT`) | `operational_fault` telemetry, no promotion, no decision-state ledger write |
| Promotion / Publication | Remote equivalence or reconciliation failure | `4` (`SYSTEM_FAULT`) | Conservative state preserved, promotion halted |
| Human Review | PR declined by reviewer | Not a new exit code; governed review outcome | Ledger records `declined_by_human`; re-promotion blocked until document hash or context digest changes |

This mapping matters because the boundary model is only trustworthy when it resolves into deterministic runtime behavior.

## A Practical Review Checklist

Use this checklist when designing or reviewing a boundary:

- What input is crossing the boundary?
- Is that input trusted, untrusted, or mixed?
- What validation occurs before the next action?
- What authority does the next component gain if validation passes?
- What state changes if the boundary is crossed?
- What happens if validation fails?
- Which exit code or non-terminal review state expresses that failure?
- Is failure explicit and traceable?
- Does the boundary preserve human authority where needed?

If a boundary cannot answer these questions clearly, it probably needs tighter design.

## Related Pages

- `LLM System Trust Model`
- `Transaction Identity and Auditability`
- `Schema Validation for LLM Output`
- `Golden Corpus Design`
- `Human-in-the-Loop Governance`
- `External State and Ledger Design`
