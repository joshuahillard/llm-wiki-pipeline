# LLM Wiki Control Plane Review

Design/code review for the proposed Windows-first `llm-wiki` validation pipeline discussed in planning.

This document is intentionally written as a build-facing review artifact, not a product spec. The goal is to turn the prior design conversation into one source of truth for:

- control-plane boundaries
- file and script responsibilities
- transaction identity rules
- failure modes and reconciliation behavior
- implementation order

---

## Review Outcome

The proposed architecture is strong in the areas that matter most:

- OS-enforced separation of roles
- a single promotion gateway instead of direct file moves
- authenticated Git transport instead of direct writes to a bare repo
- PR-based promotion rather than direct writes to `main`
- external state and audit storage outside the repo
- context-aware invalidation instead of hash-only dedupe

The remaining risk is no longer "LLM hallucination" in the abstract. It is now concentrated in long-lived state reconciliation and identity consistency across four layers:

1. runner
2. parser/wrapper
3. promotion gateway
4. remote PR state

That is good news. It means the trust model is mostly in the right place.

---

## Recommended File Inventory

The design becomes much easier to reason about if these files are treated as the canonical v1 surface area:

```text
ops/
├── Run-Validator.ps1
├── Promote-ToVerified.ps1
├── validator_runner.py
├── parse_identity.py
└── validation_result.schema.json

policy_engine/
└── _policy_bundle.md

raw_sources/
└── _source_manifest.json
```

Runtime state must live outside the repo:

```text
C:\llm-wiki-state\
├── audit_logs\
└── ledgers\
    └── validation_state.json
```

---

## Critical Invariants

These are the invariants the implementation should preserve at all times.

### 1. Identity Is Parsed Once

`parse_identity.py` must be the single source of truth for extracting:

- `source_id`
- frontmatter validity
- any future canonical identity fields

`Run-Validator.ps1` should call it.
`validator_runner.py` should import or shell out to it.
No second parser should exist.

### 2. Promotion Is Path-Bounded

`Promote-ToVerified.ps1` is the only component allowed to move a file from `provisional/` to `verified/`.

It must verify:

- canonical file containment
- manifest lineage
- provisional file hash
- clean Git index or isolated repo state

### 3. Review State Is External

Anything needed for retry safety or reconciliation must live outside the Git repo.

That includes:

- audit logs
- PR tracking
- reject/escalate cache state
- reconciliation metadata

### 4. Cache Keys Must Include Context

Skip logic cannot be based on file bytes alone.

At minimum, the cache identity must include:

- `source_id`
- canonical repo-relative path
- provisional document hash
- control-plane context digest

### 5. Namespace Must Be Preserved

Promotion into `verified/` should mirror the provisional relative path instead of flattening by filename.

Good:

```text
compiled_corpus/provisional/networking/dns.md
compiled_corpus/verified/networking/dns.md
```

Bad:

```text
compiled_corpus/verified/dns.md
```

---

## Reviewed Design Shape

### `Run-Validator.ps1`

Responsibilities:

- acquire single-instance mutex
- sync automation clone to `origin/main`
- compute context digest
- enumerate provisional drafts
- derive transaction identity through `parse_identity.py`
- skip known states only when the full transaction key matches
- invoke `validator_runner.py`
- persist reject/escalate/schema-fault states
- reconcile stale `pending_pr` entries at startup

Review notes:

- good place for startup reconciliation
- should not invent identity locally
- should persist ledger changes immediately after reconciliation
- should treat `system_fault` as non-terminal unless explicitly designed otherwise

### `parse_identity.py`

Responsibilities:

- parse beginning-of-file YAML frontmatter only
- return structured identity JSON
- be tolerant of Windows newline variants
- handle UTF-8 BOM safely

Recommended output shape:

```json
{
  "source_id": "source-uuid-123",
  "frontmatter_valid": true,
  "error": null
}
```

Review notes:

- use `utf-8-sig` or strip BOM explicitly
- keep the script tiny and deterministic
- do not let this script infer anything outside frontmatter identity

### `validator_runner.py`

Responsibilities:

- compute file hash
- validate canonical containment
- use `parse_identity.py` as the parser authority
- parse the full file for model input
- call the model
- validate model output against `validation_result.schema.json`
- pass approved candidates to `Promote-ToVerified.ps1`

Review notes:

- should not reimplement identity parsing
- should pass `context_digest` through unchanged
- should emit distinct exit codes for reject, schema fault, escalate, and system fault

### `Promote-ToVerified.ps1`

Responsibilities:

- enforce path and lineage rules
- preserve directory namespace under `verified/`
- stage exactly one intended change set
- create deterministic branch identity
- reconcile remote branch/PR state
- write `pending_pr` state to the external ledger
- fully restore local repo state on fast-path or failure

Review notes:

- this is the control plane
- it must be more conservative than every other layer
- branch and PR identity should be based on the same transaction key used by the runner

---

## Transaction Identity

The most important design choice is the transaction key.

Recommended canonical form:

```text
{source_id}:{repo_relative_path}:{document_hash}:{context_digest}
```

Example:

```text
source-uuid-123:compiled_corpus/provisional/networking/dns.md:9e5f...:4af2...
```

This should be used consistently in:

- external ledger entries
- branch metadata
- PR reconciliation logic
- audit log records

The branch name can use shortened safe fragments for readability, but the full transaction key should still be stored in ledger or PR metadata.

---

## Context Digest

The digest should represent the local control-plane rules that materially affect evaluation or promotion behavior.

Recommended inputs:

- `ops/Run-Validator.ps1`
- `ops/validator_runner.py`
- `ops/Promote-ToVerified.ps1`
- `ops/parse_identity.py`
- `ops/validation_result.schema.json`
- `policy_engine/_policy_bundle.md`
- `raw_sources/_source_manifest.json`
- `origin/main` SHA

This is best described as a local control-plane digest, not a universal truth digest. It does not include Gitea internal branch-protection state.

---

## Remaining Risks

These are the main risks still worth calling out if this is implemented.

### 1. Fast-Path Cleanup Drift

If the gateway builds a local branch and commit before discovering an equivalent remote PR, it must fully restore the workspace before exiting:

- reset to pre-transaction SHA
- move file back to `provisional/`
- unstage staged paths
- checkout `main`
- delete the ephemeral local branch
- optionally remove empty directories created under `verified/`

### 2. Remote Equivalence Must Be Stronger Than Branch Name

An existing PR should not be accepted as equivalent just because the branch name matches.

Minimum checks:

- base branch SHA matches expected `origin/main`
- remote branch tree SHA matches the intended local tree SHA

### 3. Empty Namespace Debris

Preserving folder structure is correct, but failed or short-circuited moves can leave empty directories in `verified/`.

This is not a correctness bug, but it is a deterministic-state leak worth cleaning up.

### 4. Server-Side Policy Drift

Gitea branch protection changes are outside the local digest.

That is acceptable if documented, but the limitation should be explicit.

---

## Recommended Review Comments By File

If this were a PR review, these are the changes I would insist on before merge.

### `ops/parse_identity.py`

- Handle UTF-8 BOM with `utf-8-sig`.
- Return a stable JSON schema for success and failure.
- Keep parsing limited to strict BOF frontmatter.

### `ops/validator_runner.py`

- Import or shell out to `parse_identity.py` instead of duplicating regex logic.
- Treat identity extraction failure as a system fault, not as a silent fallback.
- Pass `context_digest` into the promotion gateway.

### `ops/Run-Validator.ps1`

- Build the ledger key from parser output plus canonical repo-relative path.
- Persist startup reconciliation immediately.
- Never use regex-only source extraction locally.

### `ops/Promote-ToVerified.ps1`

- Mirror provisional namespace under `verified/`.
- Verify remote equivalence with tree SHA, not commit SHA.
- Clean fast-path local state before exiting.
- Avoid flattening all verified content into one directory.

---

## Suggested Implementation Order

1. Create `parse_identity.py`.
2. Update `validator_runner.py` to use it.
3. Update `Run-Validator.ps1` to use the same parser output for transaction identity.
4. Update `Promote-ToVerified.ps1` to preserve namespace and fully clean fast-path state.
5. Add end-to-end fixtures for:
   - approve
   - reject
   - escalate
   - schema fault
   - idempotent retry with existing PR

---

## Test Matrix

Minimum tests worth running once the scripts exist:

1. Same file, same context, existing open PR:
   - expected result: no duplicate branch, no duplicate PR, ledger healed, workspace clean

2. Same file bytes, changed `origin/main`:
   - expected result: context digest changes, file re-enters evaluation

3. Same file bytes, changed policy bundle:
   - expected result: context digest changes, file re-enters evaluation

4. Two provisional files with same basename in different directories:
   - expected result: both promote to distinct verified paths without collision

5. UTF-8 BOM frontmatter file:
   - expected result: identity parser still extracts `source_id`

6. Remote branch exists with mismatched tree:
   - expected result: hard failure, no ledger healing

---

## Bottom Line

The proposed `llm-wiki` control plane is architecturally sound if implemented with one parser authority, one promotion gateway, externalized state, and context-aware transaction identity.

The design no longer depends on trusting the LLM to "do the right thing." It depends on deterministic boundaries, explicit reconciliation, and a small number of enforceable invariants. That is the right shape for a system meant to serve as a governed knowledge substrate.
