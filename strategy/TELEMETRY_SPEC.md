# Telemetry Specification

**Version:** 1.0
**Status:** Design — Pre-Implementation
**Date:** April 6, 2026
**Owner:** Josh Hillard
**Source Authority:** Strategy Kit Rev 3.4 (P0-14, Item 4c), LLM_WIKI_CONTROL_PLANE_REVIEW.md, FMEA (F1-F17)


## Purpose

This document defines the operational telemetry contract for the LLM-Wiki Content Pipeline. It specifies the JSONL event schema emitted by `Run-Validator.ps1` and `validator_runner.py`, the Service Level Indicators (SLIs) derived from those events, and the mapping between exit codes and structured operational fault categories.

All events are written to `C:\llm-wiki-state\logs\pipeline.log` as newline-delimited JSON (JSONL). Each line is a self-contained event. The log file is append-only during a pipeline run; rotation and archival are the responsibility of the host environment.


## JSONL Event Schema

Every event shares a common envelope. Event-specific fields are nested under `payload`.

### Common Envelope

```json
{
  "timestamp": "2026-04-06T14:32:01.123Z",
  "event_type": "evaluation_completed",
  "run_id": "run-20260406-143200",
  "component": "validator_runner.py",
  "payload": {}
}
```

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO 8601 UTC) | When the event was emitted. |
| `event_type` | string (enum) | One of the defined event types below. |
| `run_id` | string | Unique identifier for the pipeline invocation. Format: `run-{YYYYMMDD}-{HHMMSS}`. Shared across all events in a single `Run-Validator.ps1` execution. |
| `component` | string | The script or module that emitted the event. One of: `Run-Validator.ps1`, `validator_runner.py`, `Promote-ToVerified.ps1`, `parse_identity.py`. |
| `payload` | object | Event-specific data. Structure varies by `event_type`. |


### Event Types

#### `pipeline_started`

Emitted once at the beginning of each `Run-Validator.ps1` execution. Captures the context digest and pipeline configuration snapshot.

```json
{
  "event_type": "pipeline_started",
  "component": "Run-Validator.ps1",
  "payload": {
    "context_digest": "4af2...SHA256",
    "origin_main_sha": "a1b2c3d4...",
    "provisional_file_count": 12,
    "validator_config": {
      "provider": "vertex_ai",
      "model_id": "gemini-1.5-pro",
      "quantization_level": null,
      "temperature": 0.0,
      "top_p": 1.0,
      "max_context_tokens": 128000,
      "system_instruction_hash": null,
      "lora_adapter_path": null,
      "tokenizer_id": "gemini-1.5-pro"
    }
  }
}
```

#### `evaluation_started`

Emitted when `validator_runner.py` begins evaluating a single file. Captures the transaction identity and token budget consumed.

```json
{
  "event_type": "evaluation_started",
  "component": "validator_runner.py",
  "payload": {
    "source_id": "networking-dns-overview",
    "repo_relative_path": "compiled_corpus/provisional/networking/dns.md",
    "document_hash": "9e5f...SHA256",
    "transaction_key": "networking-dns-overview:compiled_corpus/provisional/networking/dns.md:9e5f...:4af2...",
    "token_budget": {
      "max_context_tokens": 128000,
      "system_instruction_tokens": 1200,
      "policy_bundle_tokens": 3400,
      "article_tokens": 2800,
      "total_consumed": 7400,
      "remaining": 120600,
      "utilization_pct": 5.78
    }
  }
}
```

#### `evaluation_completed`

Emitted when `validator_runner.py` receives and validates the LLM response. Includes the decision, latency, and token metrics.

```json
{
  "event_type": "evaluation_completed",
  "component": "validator_runner.py",
  "payload": {
    "source_id": "networking-dns-overview",
    "transaction_key": "networking-dns-overview:compiled_corpus/provisional/networking/dns.md:9e5f...:4af2...",
    "decision": "approve",
    "confidence": 0.94,
    "exit_code": 0,
    "violation_count": 0,
    "latency_ms": 3420,
    "article_tokens": 2800,
    "latency_per_token_ms": 1.22,
    "model_path": "managed"
  }
}
```

#### `token_budget_exceeded`

Emitted when the pre-send token count check determines the article cannot fit within the model context window. Maps to EXIT_TOKEN_OVERFLOW (code 5) and FMEA F12.

```json
{
  "event_type": "token_budget_exceeded",
  "component": "validator_runner.py",
  "payload": {
    "source_id": "glossary-complete",
    "transaction_key": "glossary-complete:compiled_corpus/provisional/reference/glossary.md:c3d4...:4af2...",
    "token_budget": {
      "max_context_tokens": 128000,
      "total_consumed": 132400,
      "overflow_tokens": 4400
    },
    "exit_code": 5
  }
}
```

#### `promotion_started`

Emitted when `Promote-ToVerified.ps1` begins the branch-create-and-PR sequence for an approved file.

```json
{
  "event_type": "promotion_started",
  "component": "Promote-ToVerified.ps1",
  "payload": {
    "source_id": "networking-dns-overview",
    "transaction_key": "networking-dns-overview:compiled_corpus/provisional/networking/dns.md:9e5f...:4af2...",
    "provisional_path": "compiled_corpus/provisional/networking/dns.md",
    "verified_path": "compiled_corpus/verified/networking/dns.md",
    "branch_name": "auto/networking-dns-overview-9e5f"
  }
}
```

#### `promotion_succeeded`

Emitted when a PR is successfully created (or an equivalent existing PR is detected via tree SHA match).

```json
{
  "event_type": "promotion_succeeded",
  "component": "Promote-ToVerified.ps1",
  "payload": {
    "source_id": "networking-dns-overview",
    "transaction_key": "networking-dns-overview:compiled_corpus/provisional/networking/dns.md:9e5f...:4af2...",
    "pr_number": 47,
    "pr_url": "https://gitea.local/wiki/pulls/47",
    "tree_sha_match": true,
    "was_existing_pr": false
  }
}
```

#### `operational_fault`

Emitted on any non-decision exit code (3, 4, or 5). Provides structured triage information mapping to the FMEA failure modes.

```json
{
  "event_type": "operational_fault",
  "component": "validator_runner.py",
  "payload": {
    "source_id": "networking-dns-overview",
    "transaction_key": "networking-dns-overview:compiled_corpus/provisional/networking/dns.md:9e5f...:4af2...",
    "exit_code": 3,
    "fault_category": "SCHEMA_FAULT",
    "fmea_ref": "F1",
    "detail": "LLM response failed validation against validation_result.schema.json: missing required field 'confidence'",
    "recovery": "File remains in provisional/. Ledger untouched. Will retry on next pipeline run."
  }
}
```

#### `reconciliation_completed`

Emitted at the end of `Run-Validator.ps1` startup reconciliation, when stale `pending_pr` entries are resolved against Gitea API state.

```json
{
  "event_type": "reconciliation_completed",
  "component": "Run-Validator.ps1",
  "payload": {
    "stale_entries_found": 2,
    "healed_to_verified": 1,
    "healed_to_declined": 1,
    "orphaned_branches_cleaned": 0
  }
}
```

#### `pipeline_completed`

Emitted once at the end of each `Run-Validator.ps1` execution. Provides the run summary used to compute SLIs.

```json
{
  "event_type": "pipeline_completed",
  "component": "Run-Validator.ps1",
  "payload": {
    "files_evaluated": 12,
    "files_skipped_cached": 34,
    "decisions": {
      "approve": 8,
      "reject": 2,
      "escalate": 1
    },
    "faults": {
      "schema_fault": 1,
      "system_fault": 0,
      "token_overflow": 0
    },
    "promotions_attempted": 8,
    "promotions_succeeded": 8,
    "promotions_failed": 0,
    "total_latency_ms": 41200,
    "mean_latency_per_evaluation_ms": 3433
  }
}
```


## Exit Code to Fault Category Mapping

This table maps the 0-5 exit code contract (Strategy Kit Part 7) to the structured `fault_category` values used in `operational_fault` events and the corresponding FMEA references.

| Exit Code | Name | Fault Category | FMEA Ref | Telemetry Behavior |
|-----------|------|----------------|----------|---------------------|
| 0 | APPROVE | — | — | Emits `evaluation_completed` with `decision: "approve"`. |
| 1 | REJECT | — | — | Emits `evaluation_completed` with `decision: "reject"`. |
| 2 | ESCALATE | — | — | Emits `evaluation_completed` with `decision: "escalate"`. |
| 3 | SCHEMA_FAULT | `SCHEMA_FAULT` | F1 | Emits `operational_fault`. LLM response failed schema validation. File remains in provisional/. |
| 4 | SYSTEM_FAULT | `SYSTEM_FAULT` | F6, F9 | Emits `operational_fault`. Infrastructure failure (API unreachable, parser rejection, file I/O error). File remains in provisional/. |
| 5 | TOKEN_OVERFLOW | `TOKEN_OVERFLOW` | F12 | Emits `token_budget_exceeded` and `operational_fault`. File skipped. No API call made. |

Design note: Exit codes 0-2 are **decision** outcomes. Exit codes 3-5 are **fault** outcomes. Decision outcomes update the ledger. Fault outcomes do not update the ledger (the file retains its previous state or has no state). Both categories emit telemetry events.


## Service Level Indicators (SLIs)

These SLIs are computed from the JSONL event stream. They provide the deterministic data source for a future "Status Board" (Roadmap Item 9) and are designed to be calculable from a single pipeline log file with no external dependencies.

### SLI-1: Evaluation Latency per Token

**Definition:** The time (in milliseconds) for the LLM to evaluate one token of article content, measured from API request to validated response.

**Calculation:**
```
latency_per_token_ms = evaluation_completed.latency_ms / evaluation_completed.article_tokens
```

**Source event:** `evaluation_completed`

**Aggregation:** Median and P95 across all `evaluation_completed` events in a pipeline run. Reported in `pipeline_completed.mean_latency_per_evaluation_ms` as a run-level summary.

**Target:** Median < 2.0 ms/token. P95 < 5.0 ms/token. These targets are provisional and will be calibrated against real data once `validator_runner.py` is operational.

**Alert condition:** P95 > 10.0 ms/token sustained across 3 consecutive runs suggests provider degradation or model regression.

### SLI-2: PR Success Rate

**Definition:** The percentage of approved files that are successfully promoted to a Gitea PR in a single pipeline run.

**Calculation:**
```
pr_success_rate = pipeline_completed.promotions_succeeded / pipeline_completed.promotions_attempted * 100
```

**Source event:** `pipeline_completed`

**Target:** > 99% per run. Promotion failures indicate Gitea API issues (F5), branch conflicts, or workspace state corruption (F7).

**Alert condition:** Any run where `pr_success_rate < 95%` warrants immediate investigation of Gitea connectivity and branch state.

### SLI-3: Fault Rate

**Definition:** The percentage of evaluated files that produce a fault exit code (3, 4, or 5) rather than a decision exit code (0, 1, or 2).

**Calculation:**
```
fault_rate = (faults.schema_fault + faults.system_fault + faults.token_overflow) / files_evaluated * 100
```

**Source event:** `pipeline_completed`

**Target:** < 5% per run. Elevated fault rates indicate model instability (SCHEMA_FAULT), infrastructure issues (SYSTEM_FAULT), or corpus growth beyond the context window (TOKEN_OVERFLOW).

### SLI-4: Cache Hit Rate

**Definition:** The percentage of provisional files skipped due to an existing valid ledger entry (no context digest change).

**Calculation:**
```
cache_hit_rate = pipeline_completed.files_skipped_cached / (pipeline_completed.files_evaluated + pipeline_completed.files_skipped_cached) * 100
```

**Source event:** `pipeline_completed`

**Target:** > 70% in steady state (most files don't change between runs). A cache hit rate of 0% after a policy bundle change is expected and correct — it confirms the self-invalidating cache (FMEA F2) is working.


## Log File Contract

| Property | Value |
|----------|-------|
| Path | `C:\llm-wiki-state\logs\pipeline.log` |
| Format | JSONL (one JSON object per line, newline-delimited) |
| Encoding | UTF-8, no BOM |
| Rotation | Not managed by the pipeline. Host environment is responsible for log rotation. |
| Retention | Minimum 90 days recommended (aligns with SME review reduction measurement window from Strategy Kit Goals). |
| Integrity | Append-only during a pipeline run. No in-place edits. If integrity hashing is added (P1, per FMEA F8), each line includes a `line_hash` field. |


## Relationship to Other Artifacts

| Artifact | Relationship |
|----------|-------------|
| `validator_config.json` | The 9-field manifest is embedded in `pipeline_started` events. All fields except `tokenizer_id` contribute to the context digest. |
| `validation_result.schema.json` | The `evaluation_completed` event references the decision and confidence from the validated LLM output. SCHEMA_FAULT events fire when validation fails. |
| `validation_state.json` (ledger) | The ledger is the system of record for file state. Telemetry events are the operational log of how that state was reached. The ledger and the log are complementary, not redundant. |
| `VIOLATION_TAXONOMY.md` | Violation `rule_id` values appear in the ledger's full evaluation payloads (P0-14), not in telemetry events. Telemetry tracks decisions and faults, not policy details. |
| `DEFINITION_OF_DONE.md` | Gate 4 (Telemetry/Observability) requires each roadmap item to emit the mandatory events defined in this spec. |
| FMEA (Strategy Kit Part 6) | The `fmea_ref` field in `operational_fault` events maps directly to failure mode IDs F1-F17. |
