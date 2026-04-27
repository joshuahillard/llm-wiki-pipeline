# Transaction Identity and Auditability

## What This Page Is

This page explains how a single content transaction should be identified, tracked, and reconstructed across the pipeline. In a trustworthy LLM system, a transaction is not just "a file was processed." It is a specific evaluation event tied to a specific document state, a specific ruleset, and a specific system context.

This matters because accountability depends on being able to answer questions like:

- Which exact file state was evaluated?
- Under which policy and runtime conditions was it evaluated?
- What did the system decide?
- What durable state was created from that decision?
- What did a human reviewer eventually do?

If a system cannot answer those questions precisely, it may still function, but it cannot serve as a strong source of truth.

## Why Identity Is Hard in Content Systems

Identity seems easy at first. It is tempting to track content by filename, path, or article title. That works until the system encounters real-world behavior:

- two files share the same basename in different folders
- a file is edited but keeps the same path
- policy rules change even though the content does not
- the model configuration changes
- a PR is declined and later reattempted
- a document is moved or renamed

At that point, weak identity falls apart. The system begins to confuse "same file name" with "same evaluation reality." That confusion leads to stale cache hits, broken audit trails, and incorrect promotion behavior.

The solution is to define transaction identity as a composite of the things that materially determine the meaning of an evaluation.

## What a Transaction Is in This Project

In the LLM wiki architecture, a transaction should mean:

**one specific draft document, in one specific content state, evaluated under one specific control-plane context**

That definition is stronger than "the article named `dns.md`." It captures not only which article is involved, but which version of the article and which system rules were active at the time.

This is the right level of granularity because the system is not only tracking documents. It is tracking governed decisions about documents.

## Canonical Transaction Key

The core identity object for this system should be a canonical transaction key built from four parts:

```text
source_id:repo_relative_path:document_hash:context_digest
```

Example:

```text
networking-dns-overview:compiled_corpus/provisional/networking/dns.md:9e5f...:4af2...
```

This form is powerful because each part answers a different identity question:

- `source_id` answers "which logical content source is this?"
- `repo_relative_path` answers "where is it in the repository namespace?"
- `document_hash` answers "which exact content state was evaluated?"
- `context_digest` answers "under which rules-of-reality was it evaluated?"

Together, these fields create a much more trustworthy unit of identity than filename or path alone.

## Source ID

`source_id` is the logical identity of the document. It should be stable across ordinary edits and should come from the canonical frontmatter parser.

Why it matters:

- it lets the system refer to the document as a logical content object
- it survives wording changes better than hashes do
- it creates continuity across revision history

Why it is not enough by itself:

- the same `source_id` can point to different document states over time
- a document can move paths
- runtime rules can change without the `source_id` changing

This is why `source_id` is necessary but not sufficient.

## Repo-Relative Path

The repo-relative path preserves namespace and distinguishes otherwise similar files.

Why it matters:

- `networking/dns.md` and `security/dns.md` are not the same article
- promotion must preserve directory structure
- ledger and PR metadata should match real repository layout

Why it is not enough by itself:

- a path can stay the same while the document changes completely
- two evaluations of the same path under different policy contexts should not collapse into one state

For this project, "repo-relative" should be read as **repo-root relative**, not "relative to the current working directory." The path must be resolved against the Git root or an explicitly designated project root before it is normalized into the transaction key. This is the only reliable way to keep identity stable across subdirectory execution, automation clones, or alternate launch points.

The path tells the system where the document lives. It does not tell the system which version or which evaluation context it is dealing with.

## Document Hash

The document hash captures the exact content state of the draft at evaluation time.

Why it matters:

- it distinguishes one revision from another
- it allows safe re-evaluation after edits
- it prevents stale results from being reused after meaningful content changes

This is the piece that turns logical identity into content-state identity.

Without the document hash, the system cannot reliably answer whether it is looking at the same content or merely the same file location.

For this project, the document hash should be treated as an **atomic blob hash** of the entire source file, not of selected parsed fragments. Any change to the file, including a frontmatter edit, whitespace change, or body revision, creates a new content state. Trust is attached to the file as the evaluated artifact, not to a partial interpretation of the file.

## Context Digest

The context digest is one of the most important concepts in the architecture because it captures the surrounding rules and runtime conditions that shape evaluation meaning.

The current design should treat the digest as manifest-locked rather than illustrative. At a minimum, the digest must cover the material control-plane artifacts:

- `Run-Validator.ps1`
- `Promote-ToVerified.ps1`
- `validator_runner.py`
- `parse_identity.py`
- `validation_result.schema.json`
- `_policy_bundle.md`
- `origin/main` SHA

It must also include the digest-contributing fields of `validator_config.json`:

- `provider`
- `model_id`
- `quantization_level`
- `temperature`
- `top_p`
- `max_context_tokens`
- `system_instruction_hash`
- `lora_adapter_path`

`tokenizer_id` matters operationally for token budgeting, but per the current project contract it is excluded from the context digest because it is derived from `model_id`.

Why it matters:

- the same draft can deserve a different result if policy changes
- the same draft can deserve a different result if the model path changes
- the same draft should be re-evaluated when the control plane changes materially

Without the context digest, the system would accidentally treat old approvals as permanent truths. The digest makes trust self-invalidating when the system itself changes.

## Why These Fields Belong Together

Each field solves a different identity problem:

- `source_id` solves logical continuity
- `path` solves namespace fidelity
- `document_hash` solves revision fidelity
- `context_digest` solves rule fidelity

Any weaker key leaves room for confusion:

- `source_id` alone is too broad
- `path` alone is too fragile
- `document_hash` alone loses logical continuity
- `source_id + hash` still misses runtime drift

The canonical transaction key works because it represents not only the document, but the governed evaluation event.

## Audit Trail Design

A good audit trail allows a reviewer to start from any important artifact and navigate outward.

For example, from a verified article you should be able to trace to:

- the source document identity
- the evaluated content state
- the evaluation output
- the policy contract in force
- the runtime model configuration
- the PR that carried promotion
- the human review outcome

Likewise, from a ledger entry you should be able to trace to:

- the original content path
- the decision type
- the model response
- the operational logs
- any later merge or decline event

Auditability is not just about storing lots of data. It is about storing enough structured data that reconstruction is possible and reliable.

For this project, auditability also includes decline semantics. A human decline is not a vague historical note. It is a governed outcome that must be tied to the exact content state and context under review.

## What Should Be Traceable End-to-End

At minimum, the system should be able to reconstruct:

1. the original draft file
2. the parser-derived identity
3. the transaction key
4. the full validated model output
5. the model config snapshot
6. the decision outcome
7. the telemetry for the evaluation and promotion attempt
8. the PR state and branch identity
9. the final human outcome

If any one of these becomes untraceable, the system becomes harder to defend during review, debugging, or incident analysis.

That traceability should include the T7 decline case explicitly: if a PR is declined, the ledger state should be tied to the specific `document_hash` and `context_digest` that produced the promotion attempt.

## Identity Drift and Split-Brain Risks

One of the main threats to auditability is identity drift, where different parts of the system begin to refer to the "same" transaction in inconsistent ways.

Common causes:

- multiple frontmatter parsers
- local reconstruction of `source_id`
- inconsistent path normalization
- hashing different content representations
- building cache keys differently in different layers
- branch names derived from different identity fragments than ledger entries

This is why identity logic should be centralized and reused. It is better to have one well-defined identity authority than many convenient local shortcuts.

## Safe Branch Identity vs Full Transaction Identity

The full transaction key is the authoritative identity object, but it is not the same thing as a safe Git branch name.

Why this distinction matters:

- the full key contains separators that are not ideal for branch naming
- the full key may be too long for practical branch use
- Git and hosting systems impose readability and length constraints

For this reason, branch identity should use a safe derived form for readability, while the full transaction key remains stored in ledger records, PR metadata, and audit logs.

A safe branch form should be:

```text
auto/{source_id}/{short_hash}
```

Where `short_hash` is a stable shortened fragment derived from the transaction identity material, typically using the leading characters of the `document_hash` together with context-sensitive entropy. The branch name is therefore a readable handle, not the canonical audit object.

The rule is:

- branch name = safe operational alias
- full transaction key = authoritative identity

## Example Transaction Walkthrough

Consider a draft article at:

`compiled_corpus/provisional/networking/dns.md`

The parser extracts:

- `source_id = networking-dns-overview`

The file contents hash to:

- `document_hash = 9e5f...`

The active control plane and model config hash to:

- `context_digest = 4af2...`

The canonical transaction key becomes:

```text
networking-dns-overview:compiled_corpus/provisional/networking/dns.md:9e5f...:4af2...
```

The evaluator produces a structured decision. The ledger stores that decision under the transaction key. Promotion logic derives its branch identity from the same transaction. A human later declines the PR. That decline is recorded against the same transaction lineage.

If that PR is declined, the decline should be treated as hash-locked to that exact `document_hash` under that exact `context_digest`. The system must not re-promote the same content under the same context just because a later run occurred. The lock breaks only when:

- the file changes, producing a new `document_hash`, or
- the control plane changes, producing a new `context_digest`

Now suppose the policy bundle changes but the article does not. The new `context_digest` changes the transaction key, which forces re-evaluation. This is correct behavior because the trust basis changed even though the draft did not.

## Auditability Checklist

Use this checklist when reviewing identity and traceability design:

- Is there one canonical parser for identity fields?
- Is the transaction key composite rather than single-field?
- Does the key distinguish content changes from rule changes?
- Is the path resolved root-relatively rather than from an arbitrary working directory?
- Is namespace preserved in identity and promotion logic?
- Is the document hash an atomic hash of the entire file?
- Can a ledger entry be tied back to the exact evaluated document?
- Is the model configuration snapshot retained?
- Is the context digest built from the precise contract inputs rather than a vague notion of "config"?
- Can human review outcomes be linked back to prior evaluation state?
- Are decline outcomes hash-locked until document hash or context digest changes?
- Is branch naming treated as a safe alias rather than the full identity object?
- Do logs and PR metadata use the same identity language?

If the answer to any of these is no, auditability is weaker than it appears.

## Related Pages

- `LLM System Trust Model`
- `Trust Boundaries in LLM Pipelines`
- `Schema Validation for LLM Output`
- `External State and Ledger Design`
- `Review Workflow and Promotion Lifecycle`
