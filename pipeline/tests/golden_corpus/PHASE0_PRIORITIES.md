# Phase 0 Golden Corpus — Priority Guide

Based on the current project state and implementation roadmap, here is the recommended order for building the bootstrap corpus.


## What You Have Done (Design Complete)

- parse_identity.py: written and functional (P0-1, P0-10)
- validation_result.schema.json: defined (5 required fields)
- validator_config.json: v1 defaults in place (Vertex AI / Gemini 1.5 Pro)
- Folder infrastructure: provisional/, verified/, golden_corpus/{approve,reject,escalate,adversarial}
- Strategy Kit Rev 3.4: all 14 P0 requirements documented
- 23 seed corpus files in place (3 approve, 4 reject, 3 escalate, 13 adversarial)


## Priority 1: Validate What You Already Have (This Week)

**Goal:** Prove that parse_identity.py handles all adversarial cases correctly.

You can test this today without any LLM integration. Run parse_identity.py against every adversarial file and confirm the output matches the CORPUS_MANIFEST expectations:

```powershell
# From the pipeline directory
Get-ChildItem tests\golden_corpus\adversarial\*.md | ForEach-Object {
    Write-Host "--- $($_.Name) ---"
    python parse_identity.py $_.FullName
    Write-Host "Exit code: $LASTEXITCODE`n"
}
```

**What to look for:**
- ADV-001 through ADV-005, ADV-007, ADV-008, ADV-011: exit code 4, structured error JSON
- ADV-003, ADV-006, ADV-010, ADV-012: exit code 0, valid parsed output
- ADV-009: exit code 0 (parser succeeds), but note this for LLM evaluation later
- ADV-013: exit code 0 (parser succeeds), body injection is an LLM-layer concern

If any file produces an unexpected result, you've found a parse_identity.py bug before it reaches production. Fix it now.


## Priority 2: Build validator_runner.py (Items 1-2)

**Goal:** Get the LLM evaluation loop working so you can test approve/reject/escalate decisions.

This is blocked by Open Question #1 (which managed API provider), but your validator_config.json already has v1 defaults pointing at Vertex AI / Gemini 1.5 Pro. You can build against that and swap later.

**What validator_runner.py needs to do with the corpus:**
1. Accept a file path from Run-Validator.ps1
2. Call parse_identity.py to extract frontmatter (already done)
3. Load the policy bundle
4. Construct the LLM prompt: system instruction + policy bundle + article content
5. Send to the model, get a response
6. Validate the response against validation_result.schema.json
7. Return the appropriate exit code (0-5)

Once validator_runner.py can evaluate a single file, run it against all approve/reject/escalate corpus files.


## Priority 3: Expand the Corpus for Calibration (Items 2, 4e)

Once validator_runner.py produces actual decisions, you'll immediately discover calibration issues. This is expected. The corpus exists to make those issues visible.

**Likely calibration problems and what to add:**

**Problem: LLM rejects articles it should approve.**
- Add more approve examples with varying lengths, formats, and topics
- Add examples with minor imperfections that are acceptable (slight informality, non-standard but valid formatting)
- Test whether the policy bundle prompt is too strict

**Problem: LLM approves articles it should reject.**
- Add more subtle reject cases: articles that are mostly correct but have one significant factual error buried in otherwise good content
- Add articles with plausible-sounding but wrong statistics
- Add articles that plagiarize or closely paraphrase external sources

**Problem: LLM never escalates (always commits to approve or reject).**
- Add more escalate examples that are explicitly ambiguous
- Check whether your system instruction tells the LLM that escalation is a valid and expected outcome
- Add articles where the content quality is fine but the topic requires domain expertise the LLM can't verify

**Problem: LLM decision is inconsistent (same file gets different decisions on re-run).**
- This is why temperature is 0.0 in validator_config.json
- If still inconsistent, the prompt may be underspecified — add more explicit decision criteria to the policy bundle


## Priority 4: Token Overflow Cases (Item 4d)

**Goal:** Test that token budget enforcement works before expensive API calls.

You need at least one article that approaches or exceeds the context window. The v1 config sets max_context_tokens at 128,000. Your prompt will consume some of that (system instruction + policy bundle), leaving the remainder for the article.

**How to create these:**
- Take a legitimate article and pad it to 95% of the remaining token budget
- Create a file that is exactly at the limit (should pass)
- Create a file that is 1 token over the limit (should trigger EXIT_TOKEN_OVERFLOW)
- You'll need to know the actual token count, which depends on the tokenizer — this is why Item 4d depends on Item 4b

These files aren't in the seed corpus because they require knowing the exact token budget after prompt construction. Add them once validator_runner.py can compute token counts.


## Priority 5: Context Digest Change Cases (Item 3)

**Goal:** Prove that changing the context digest forces re-evaluation.

This requires Run-Validator.ps1 (Item 3) to be functional. The test is:

1. Evaluate a file → gets APPROVE → recorded in ledger
2. Change validator_config.json (e.g., bump temperature from 0.0 to 0.1)
3. Re-run the pipeline
4. Confirm the file is re-evaluated (because the context digest changed) rather than skipped as already-approved

This isn't a corpus file — it's a pipeline integration test. But it exercises the same files you already have (any approve example works).


## What NOT to Focus On Yet

- **Phase 1 production corpus**: you have no production pipeline yet, so there are no reviewer outcomes to collect
- **Phase 2 rolling holdout**: you need Phase 1 data first
- **LoRA/DPO training data**: the ledger retention schema (P0-14) handles this automatically once the pipeline runs — don't manually create training data
- **Parity harness results**: blocked until both managed and self-hosted model paths are operational (Item 4f)
- **Multi-language content**: nice to have but not blocking; focus on English-language edge cases first


## Corpus Growth Targets

| Milestone | Approve | Reject | Escalate | Adversarial | Total |
|-----------|---------|--------|----------|-------------|-------|
| Seed (now) | 3 | 4 | 3 | 13 | 23 |
| After Priority 1 (parse_identity validated) | 3 | 4 | 3 | 13 | 23 (no change, just validated) |
| After Priority 3 (calibration round 1) | 8-10 | 8-10 | 5-7 | 15 | 36-42 |
| After Priority 4 (token overflow) | 8-10 | 8-10 | 5-7 | 18 | 39-45 |
| Parity harness ready (Item 4f) | 15+ | 15+ | 10+ | 20+ | 60+ |

The parity harness needs enough variety that a 90% agreement rate is meaningful. 60+ files with good category coverage is a reasonable Phase 0 target.
