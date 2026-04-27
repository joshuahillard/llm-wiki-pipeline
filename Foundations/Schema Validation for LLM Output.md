# Schema Validation for LLM Output

## What This Page Is

This page explains why LLM output must be treated as untrusted until it passes schema validation, and how schema validation acts as a control mechanism in the pipeline.

In this project, the model is allowed to produce a recommendation, not to define its own interface. The schema is the contract that tells the software what shape of output is acceptable. This gives the control plane a deterministic way to accept or reject model responses before they influence state.

## Why LLM Output Cannot Be Trusted Directly

LLMs are good at producing plausible structure, but plausible structure is not the same as guaranteed structure.

A model may return:

- valid JSON
- invalid JSON
- JSON wrapped in markdown fences
- missing required fields
- extra unsupported fields
- wrong enum values
- strings where numbers are expected
- structurally valid output that still reflects poor judgment

This means the raw output of the model is not yet safe to process. Even if it looks clean to a human reader, software should not assume it conforms to the expected contract.

This is especially important in governed systems because an unchecked model response can:

- bypass intended decision paths
- poison ledger state
- open promotion workflows incorrectly
- produce inconsistent downstream behavior

## Structured Output as a Control Mechanism

Schema validation is not just a formatting convenience. It is a way to preserve control over the boundary between probabilistic output and deterministic software.

Without schema validation:

- the model effectively shapes the downstream interface
- small format drifts can break routing behavior
- debugging becomes inconsistent and manual

With schema validation:

- the control plane defines the output contract
- invalid responses are rejected predictably
- downstream components can rely on a stable envelope

In other words, schema validation prevents the model from improvising its own protocol.

## What the Validation Schema Should Enforce

The validation schema should define exactly what the system needs in order to act safely, no more and no less.

For this project, the schema should enforce:

- a decision field
- a bounded confidence field
- non-empty reasoning text
- a structured list of policy violations
- a structured list of recommendations

The goal is not to capture every nuance of the model's internal thinking. The goal is to capture a reliable operational interface.

For this project, that interface should be treated as a hard contract, not a loose formatting preference.

## Required Fields

Required fields matter because downstream routing depends on them.

Examples:

- `decision` tells the control plane whether the result is approve, reject, or escalate
- `confidence` provides calibration context
- `reasoning` gives human-auditable explanation
- `policy_violations` ties the decision to the rule taxonomy
- `recommendations` supports author remediation

If a required field is missing, the system no longer has a complete decision object. That should be treated as a fault, not as a partial success.

The raw model response contract is therefore:

- `decision`
- `confidence`
- `reasoning`
- `policy_violations`
- `recommendations`

Any omission is a schema failure.

For `decision = approve`, `policy_violations` must still be present and must be an empty array `[]`. A missing field, `null`, or alternate placeholder value is a `SCHEMA_FAULT`, not an acceptable shortcut.

## Field Constraints and Allowed Values

Constraints matter because the model will often produce something close to correct, but "close" is not sufficient for deterministic systems.

Useful constraints include:

- enum restrictions for `decision`
- numeric bounds for `confidence`
- max length for free-text fields
- item structure for `policy_violations`
- allowed severity values
- max count for recommendations
- `additionalProperties: false` where strictness is needed

These constraints do two things:

1. They reduce ambiguity for downstream code.
2. They limit how much unplanned structure the model can introduce.

For this project, several of these constraints should be treated as exact mathematical or structural rules:

- `decision` must be one of `approve`, `reject`, or `escalate`
- `confidence` must be a number in the closed interval `[0.0, 1.0]`
- percentage-style values such as `94` are invalid
- string values such as `"high"` are invalid
- values such as `1.1` or `-0.1` are invalid
- `reasoning` must be non-empty and must not exceed the schema limit of `4096` characters
- `policy_violations` items must match the nested object contract exactly

## Additional Properties and Why They Matter

One subtle but important schema choice is whether to allow extra fields.

If extra fields are allowed freely:

- the model can invent unsupported semantics
- downstream consumers may start depending on fields that are unofficial
- different runs may produce structurally inconsistent payloads

If extra fields are disallowed:

- the interface stays tight
- any unsupported field becomes a detectable contract violation
- versioning remains deliberate instead of accidental

For this project, strictness is not merely the better default. It is the required contract posture.

`additionalProperties: false` should be mandatory:

- at the root object
- on each `policy_violations` item
- on any other nested structured object introduced by the contract

Any field not explicitly defined by `validation_result.schema.json` should be treated as a schema failure.

## Decision Outcomes and Exit Code Mapping

The schema and the runtime contract should work together.

Typical mapping:

- `approve` -> exit code `0`
- `reject` -> exit code `1`
- `escalate` -> exit code `2`
- schema-invalid response -> exit code `3`

This separation matters because decision outcomes and fault outcomes are not the same thing.

- `approve`, `reject`, and `escalate` are governed decisions
- schema failure is an operational fault

That distinction keeps the control plane honest. A malformed response is not a valid rejection. It is a failed interaction with the model interface.

## What Happens on Schema Failure

When schema validation fails, the system should:

- classify the event as a schema fault
- avoid promotion behavior
- avoid writing decision state as though evaluation succeeded
- emit telemetry for diagnosis
- leave the content in a conservative state

The important point is that schema failure is not a content verdict. It is a failure of the model to satisfy the software contract.

For this project, that means:

- emit an `operational_fault` telemetry event
- use `fault_category: "SCHEMA_FAULT"`
- use `fmea_ref: "F1"`
- prohibit decision-state writes to `validation_state.json`
- leave the transaction without a decision ledger entry so a clean retry is possible

This is why schema faults should be observable and recoverable, but should not be mistaken for article quality signals.

## Taxonomy Binding

Structural validation alone is not sufficient for `rule_id` values. The software, not the model, owns the policy taxonomy.

For this project, a `policy_violations[].rule_id` is not fully valid unless it binds to the active violation taxonomy. That means the accepted ID set must come from the concrete rule IDs defined in `VIOLATION_TAXONOMY.md`, including:

- `ACCURACY-001`
- `ACCURACY-002`
- `ACCURACY-003`
- `ACCURACY-004`
- `ACCURACY-005`
- `COMPLETENESS-001`
- `COMPLETENESS-002`
- `COMPLETENESS-003`
- `COMPLETENESS-004`
- `SECURITY-001`
- `SECURITY-002`
- `SECURITY-003`
- `FORMATTING-001`
- `FORMATTING-002`
- `NEUTRALITY-001`

Whether this binding is enforced through a literal schema enum or an immediate post-schema contract check, the effect should be the same:

- taxonomy-valid rule ID -> continue
- invented or unknown rule ID -> `SCHEMA_FAULT`

This matters because a syntactically correct but nonexistent `rule_id` is still contract-invalid.

## Cross-Field Validation Rules

Some failures are not about individual field types. They are about impossible combinations of fields that violate the governance contract.

For this project, the validator contract should reject at least the following combinations:

- `decision = approve` with any `policy_violations` item having `severity = critical`
- `decision = approve` with any `policy_violations` item having `severity = major`
- `decision = approve` with a non-empty `policy_violations` array unless the remaining violations are contract-valid non-blocking observations
- `decision = approve` with `policy_violations = null`

The most important rule is the first: a critical violation cannot coexist with approval. If the model produces a "critical approval," that response is not merely poor judgment. It is contract-invalid and should be treated as a `SCHEMA_FAULT`.

Whether these checks live inside a richer schema layer or in an immediate post-schema validation step, the effect should be deterministic and identical.

## Raw Output Contract vs Post-Processing Contract

This project has two related but distinct objects:

1. the raw model output validated by `validation_result.schema.json`
2. the post-processed feedback object used for author-facing delivery

This distinction matters because `location` metadata belongs to the feedback projection contract, not to the raw model-output contract.

The raw model output should contain only the fields allowed by `validation_result.schema.json`. If the model invents a `location` field in the raw response, that field should be rejected by the strict no-extra-properties contract.

The post-processing layer may then attach optional location metadata for feedback rendering, using the shape defined by `FEEDBACK_SPEC.md`:

- `type` = `section`, `line`, or `frontmatter`
- `reference` = human-readable anchor
- `line_start` = integer
- `line_end` = integer

This keeps the contract clean:

- raw model schema governs evaluation output
- post-processing contract governs author-facing augmentation

## Examples of Valid Output

Example of structurally valid output:

```json
{
  "decision": "reject",
  "confidence": 0.91,
  "reasoning": "The article contains a factual contradiction about TCP and UDP behavior.",
  "policy_violations": [
    {
      "rule_id": "ACCURACY-001",
      "description": "TCP is described as connectionless and UDP as connection-oriented.",
      "severity": "critical"
    }
  ],
  "recommendations": [
    "Correct the protocol descriptions and verify the transport layer section against authoritative networking references."
  ]
}
```

This does not prove the decision is correct, but it does prove the response is safe to process further.

## Examples of Invalid Output

Example of invalid output:

```json
{
  "decision": "deny",
  "confidence": "high",
  "reasoning": "",
  "violations": [
    "ACCURACY-001"
  ]
}
```

Why this is invalid:

- `decision` is not an allowed enum value
- `confidence` is not numeric
- `reasoning` is empty
- `policy_violations` is missing
- `recommendations` is missing
- `violations` is not part of the supported contract

This response may still be understandable to a human, but it is not acceptable system input.

Another invalid example:

```json
{
  "decision": "approve",
  "confidence": 94,
  "reasoning": "Looks good.",
  "policy_violations": [],
  "recommendations": []
}
```

Why this is invalid:

- `confidence` is outside the allowed `[0.0, 1.0]` range
- percentage interpretation is not allowed by the contract

Another invalid example:

```json
{
  "decision": "approve",
  "confidence": 0.88,
  "reasoning": "The article is acceptable overall.",
  "policy_violations": [
    {
      "rule_id": "SECURITY-001",
      "description": "The article contains a plaintext token.",
      "severity": "critical"
    }
  ],
  "recommendations": []
}
```

Why this is invalid:

- a `critical` violation cannot coexist with `decision = approve`
- the response violates the governance contract even though its field types are individually valid

## Common Failure Modes

Common schema-related failure patterns include:

### 1. Markdown-wrapped JSON

The model may place valid JSON inside code fences. A parser may choose to normalize that before schema validation, but the normalized object must still satisfy the schema.

### 2. Partial structure

The model may provide a decision but omit violation details or recommendations.

### 3. Empty-violation paradox

The model may return `approve` while omitting `policy_violations`, setting it to `null`, or otherwise failing to provide the required empty array.

### 4. Semantic drift in field names

The model may emit `violations` instead of `policy_violations`, or `explanation` instead of `reasoning`.

### 5. Invalid nested objects

The top-level structure may be correct while nested objects violate severity or rule ID constraints.

### 6. Cross-field contradiction

The model may return a structurally valid object whose decision contradicts the severities in `policy_violations`.

### 7. Unknown taxonomy values

The model may emit a well-formed but nonexistent `rule_id`. That is not a policy interpretation issue. It is a contract failure.

### 8. Payload bloat

The model may emit oversized `reasoning` or recommendation text that is technically readable but operationally unsafe for durable storage.

### 9. Overly permissive contracts

If the schema is too loose, invalid or inconsistent model behavior may slip into durable state without detection.

## Design Tradeoffs: Strict vs Flexible Schemas

There is a real tradeoff here.

### Strict schema

Benefits:

- predictable downstream behavior
- stronger observability
- better contract discipline

Costs:

- more schema faults when the model drifts
- more careful prompt design required

### Flexible schema

Benefits:

- fewer hard failures
- easier short-term experimentation

Costs:

- more ambiguity
- greater drift risk
- more hidden complexity in downstream consumers

For this project, the better choice is a strict schema because the system is designed around accountability and governed publication, not casual experimentation.

In practice, this means:

- strict field lists
- strict numeric bounds
- strict enum values
- strict nested-object rules
- strict taxonomy binding

## What Schema Validation Does Not Solve

Schema validation is necessary, but it is not enough.

It does not prove:

- the article is factually correct
- the decision is well calibrated
- the severity mapping is appropriate
- the model is unbiased
- the policy taxonomy is complete

Schema validation protects the structure of the interaction. It does not replace policy evaluation, corpus testing, governance, or human review.

## Review Checklist

Use this checklist when reviewing schema design:

- Are required fields truly required by the control plane?
- Are enum values narrow and intentional?
- Is `confidence` constrained mathematically to `[0.0, 1.0]`?
- Is `policy_violations` required even for approvals, with `[]` as the only valid empty state?
- Is `reasoning` bounded to the actual schema cap rather than left operationally unbounded?
- Are nested structures constrained enough to be useful?
- Are extra fields blocked unless explicitly versioned?
- Are rule IDs bound to the authoritative taxonomy rather than only pattern-checked?
- Are cross-field contradictions rejected deterministically?
- Is raw model output kept separate from post-processing fields like `location`?
- Does schema failure map to a distinct fault path?
- Can downstream systems rely on validated output without ad hoc patching?
- Does the schema reflect operational needs rather than prompt convenience?

If the answer to these questions is unclear, the schema is probably too loose.

## Related Pages

- `LLM System Trust Model`
- `Trust Boundaries in LLM Pipelines`
- `Transaction Identity and Auditability`
- `Golden Corpus Design`
- `LLM Evaluation System Design`
