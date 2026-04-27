# CTX-001: Context Digest Change Test

## Type
Pipeline integration test (not a single-file fixture)

## What It Tests
Strategy Kit P0-2: "any change produces a new digest" and the resulting cache invalidation.
FMEA F2: "Context drift renders cached evaluations stale."

## Prerequisites
- Run-Validator.ps1 operational (Item 3)
- Ledger writes functional
- validator_config.json in place

## Procedure

### Step 1: Baseline Evaluation
```powershell
# Run pipeline against this fixture
# Expected: article evaluated, APPROVE recorded in ledger
```

### Step 2: Rotate the Digest
```powershell
# Modify any digest-contributing field in validator_config.json
# Example: change temperature from 0.0 to 0.1
$config = Get-Content pipeline\ops\validator_config.json | ConvertFrom-Json
$config.temperature = 0.1
$config | ConvertTo-Json | Set-Content pipeline\ops\validator_config.json
```

### Step 3: Re-run Pipeline
```powershell
# Expected: article is RE-EVALUATED (not skipped as cached)
# Ledger should show a new evaluation entry under the new context digest
```

### Expected Outcome
- `expected_parser`: success
- `expected_exit_code`: 0 (APPROVE) on both runs
- `expected_behavior`: Two distinct ledger entries with different context digests for the same transaction key (same source_id + path + doc_hash, different digest)

### Verification
```powershell
# Query ledger for all entries matching this source_id
# Confirm: 2 entries, different context_digest values, both APPROVE
```
