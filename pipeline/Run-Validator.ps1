[CmdletBinding()]
param(
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$StateRoot = "C:\llm-wiki-state",
    [string]$ProvisionalRoot = $null,
    [string]$VerifiedRoot = $null,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PipelineRoot = $PSScriptRoot
$PythonExe = "python"
$ParserPath = Join-Path $PipelineRoot "parse_identity.py"
$ValidatorPath = Join-Path $PipelineRoot "validator_runner.py"
$ConfigPath = Join-Path $PipelineRoot "ops\validator_config.json"
$SchemaPath = Join-Path $PipelineRoot "validation_result.schema.json"
$SystemPromptPath = Join-Path $PipelineRoot "SYSTEM_PROMPT.md"
$PolicyBundlePath = Join-Path $PipelineRoot "policy_engine\_policy_bundle.md"
$PromoteScriptPath = Join-Path $PipelineRoot "Promote-ToVerified.ps1"
if (-not $ProvisionalRoot) {
    $ProvisionalRoot = Join-Path $PipelineRoot "provisional"
}
if (-not $VerifiedRoot) {
    $VerifiedRoot = Join-Path $PipelineRoot "verified"
}
$LogRoot = Join-Path $StateRoot "logs"
$LedgerRoot = Join-Path $StateRoot "ledger"
$AuditRoot = Join-Path $StateRoot "audit"
$LogPath = Join-Path $LogRoot "pipeline.log"

function Ensure-Directory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Get-FileSha256 {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-RepoRelativePath {
    param(
        [string]$Path,
        [string]$Root
    )

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRoot = [System.IO.Path]::GetFullPath($Root)

    if (-not $fullRoot.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $fullRoot = $fullRoot + [System.IO.Path]::DirectorySeparatorChar
    }

    if (-not $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path '$Path' is outside repo root '$Root'."
    }

    return $fullPath.Substring($fullRoot.Length).Replace('\', '/')
}

function Read-JsonFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "JSON file not found: $Path"
    }

    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-EffectiveValidatorConfigObject {
    param([string]$SourceConfigPath)

    $config = Read-JsonFile -Path $SourceConfigPath

    # Credential-aware fallback: honour the configured provider when the
    # required credentials are present.  Fall back to stub (with a warning)
    # when they are not, so the test harness and dry-run paths still work
    # without live API keys.
    $provider = [string]$config.provider
    if ($provider -eq "anthropic") {
        if (-not $env:ANTHROPIC_API_KEY) {
            Write-Warning "ANTHROPIC_API_KEY not set - falling back to stub provider."
            $config.provider = "stub"
        }
    }
    elseif ($provider -eq "vertex_ai") {
        # Vertex AI integration is not yet wired in validator_runner.py.
        Write-Warning "vertex_ai provider not yet implemented - falling back to stub provider."
        $config.provider = "stub"
    }
    # stub and any other value pass through to validator_runner.py, which
    # will raise ConfigError for unknown providers.

    return $config
}

function Get-OriginMainMarker {
    param([string]$Root)

    $headFile = Join-Path $Root ".git\HEAD"
    if (Test-Path -LiteralPath $headFile) {
        return (Get-FileSha256 -Path $headFile)
    }

    return "no-git-head"
}

function Get-ContextDigest {
    param(
        [string]$Root,
        [string]$PipelineRootPath,
        [object]$EffectiveConfig
    )

    $digestParts = @(
        "run_validator=" + (Get-FileSha256 -Path (Join-Path $PipelineRootPath "Run-Validator.ps1"))
        "promote=" + (Get-FileSha256 -Path $PromoteScriptPath)
        "parser=" + (Get-FileSha256 -Path $ParserPath)
        "validator_runner=" + (Get-FileSha256 -Path $ValidatorPath)
        "schema=" + (Get-FileSha256 -Path $SchemaPath)
        "policy_bundle=" + (Get-FileSha256 -Path $PolicyBundlePath)
        "origin_main_marker=" + (Get-OriginMainMarker -Root $Root)
        "provider=" + [string]$EffectiveConfig.provider
        "model_id=" + [string]$EffectiveConfig.model_id
        "quantization_level=" + [string]$EffectiveConfig.quantization_level
        "temperature=" + [string]$EffectiveConfig.temperature
        "top_p=" + [string]$EffectiveConfig.top_p
        "max_context_tokens=" + [string]$EffectiveConfig.max_context_tokens
        "system_instruction_hash=" + [string]$EffectiveConfig.system_instruction_hash
        "lora_adapter_path=" + [string]$EffectiveConfig.lora_adapter_path
    )

    $material = [System.Text.Encoding]::UTF8.GetBytes(($digestParts -join "`n"))
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($material)
    }
    finally {
        $sha.Dispose()
    }

    return ([System.BitConverter]::ToString($hashBytes)).Replace('-', '').ToLowerInvariant()
}

function Get-SafeLedgerName {
    param([string]$TransactionKey)

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($TransactionKey)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($bytes)
    }
    finally {
        $sha.Dispose()
    }

    $keyHash = ([System.BitConverter]::ToString($hashBytes)).Replace('-', '').ToLowerInvariant()
    $timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffffffZ")
    return "${keyHash}_${timestamp}.json"
}

function Write-JsonlEvent {
    param(
        [string]$EventType,
        [hashtable]$Payload
    )

    $record = [ordered]@{
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
        event_type    = $EventType
    }

    foreach ($key in $Payload.Keys) {
        $record[$key] = $Payload[$key]
    }

    $json = $record | ConvertTo-Json -Depth 8 -Compress
    Add-Content -LiteralPath $LogPath -Value $json -Encoding UTF8
}

function Write-LedgerEntry {
    param([hashtable]$Entry)

    $fileName = Get-SafeLedgerName -TransactionKey $Entry.transaction_key
    $ledgerPath = Join-Path $LedgerRoot $fileName
    $json = $Entry | ConvertTo-Json -Depth 10
    Set-Content -LiteralPath $ledgerPath -Value $json -Encoding UTF8
    return $ledgerPath
}

function Invoke-JsonPython {
    param([string[]]$Arguments)

    $stderrFile = [System.IO.Path]::GetTempFileName()

    try {
        $stdoutObjects = & $PythonExe @Arguments 2> $stderrFile
        $exitCode = $LASTEXITCODE
        $stdout = ($stdoutObjects | Out-String).Trim()
        $stderr = Get-Content -LiteralPath $stderrFile -Raw -Encoding UTF8

        return @{
            ExitCode = $exitCode
            StdOut   = $stdout
            StdErr   = $stderr
        }
    }
    finally {
        Remove-Item -LiteralPath $stderrFile -Force -ErrorAction SilentlyContinue
    }
}

function New-FeedbackSidecar {
    param(
        [string]$ArticlePath,
        [object]$ValidationResult
    )

    $sidecarPath = $ArticlePath + ".feedback.md"
    $fileName = Split-Path -Leaf $ArticlePath
    $lines = @(
        "# Validation Feedback: $fileName",
        "",
        "Decision: $($ValidationResult.decision)",
        "",
        "## Summary",
        "",
        $ValidationResult.reasoning,
        ""
    )

    if ($ValidationResult.policy_violations.Count -gt 0) {
        $lines += "## Policy Violations"
        $lines += ""
        foreach ($violation in $ValidationResult.policy_violations) {
            $lines += "- $($violation.rule_id) ($($violation.severity)): $($violation.description)"
        }
        $lines += ""
    }

    if ($ValidationResult.recommendations.Count -gt 0) {
        $lines += "## Recommendations"
        $lines += ""
        foreach ($rec in $ValidationResult.recommendations) {
            $lines += "- $rec"
        }
        $lines += ""
    }

    Set-Content -LiteralPath $sidecarPath -Value ($lines -join "`r`n") -Encoding UTF8
}

function Write-TempValidatorConfig {
    param([object]$Config)

    $tempPath = Join-Path ([System.IO.Path]::GetTempPath()) ("llm-wiki-bootstrap-" + [System.Guid]::NewGuid().ToString("N") + ".json")
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tempPath, ($Config | ConvertTo-Json -Depth 6), $utf8NoBom)
    return $tempPath
}

function Test-DeclinedHashLock {
    param(
        [string]$DocumentHash,
        [string]$ContextDigest
    )

    $ledgerFiles = Get-ChildItem -LiteralPath $LedgerRoot -Filter *.json -ErrorAction SilentlyContinue
    foreach ($lf in $ledgerFiles) {
        try {
            $entry = Get-Content -LiteralPath $lf.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        catch {
            # Skip unreadable ledger files - the lock check is a guardrail,
            # not a load-bearing wall.  A corrupted file must not kill the run.
            continue
        }

        if ([string]$entry.document_hash -eq $DocumentHash -and
            [string]$entry.context_digest -eq $ContextDigest -and
            [string]$entry.reviewer_outcome -eq "declined_by_human") {
            return @{
                Locked            = $true
                LedgerPath        = $lf.FullName
                ReviewerTimestamp = [string]$entry.reviewer_timestamp
                TransactionKey    = [string]$entry.transaction_key
            }
        }
    }

    return @{ Locked = $false }
}

Ensure-Directory -Path $LogRoot
Ensure-Directory -Path $LedgerRoot
Ensure-Directory -Path $AuditRoot

if (-not (Test-Path -LiteralPath $ParserPath)) {
    throw "parse_identity.py not found: $ParserPath"
}

if (-not (Test-Path -LiteralPath $ValidatorPath)) {
    throw "validator_runner.py not found: $ValidatorPath"
}

$effectiveConfigObject = Get-EffectiveValidatorConfigObject -SourceConfigPath $ConfigPath
$effectiveConfigPath = Write-TempValidatorConfig -Config $effectiveConfigObject
$contextDigest = Get-ContextDigest -Root $RepoRoot -PipelineRootPath $PipelineRoot -EffectiveConfig $effectiveConfigObject
$files = @(Get-ChildItem -LiteralPath $ProvisionalRoot -Recurse -File -Filter *.md |
    Where-Object { $_.Name -notlike "*.feedback.md" })

Write-JsonlEvent -EventType "run_started" -Payload @{
    repo_root       = $RepoRoot
    context_digest  = $contextDigest
    dry_run         = [bool]$DryRun
    file_count      = $files.Count
}

$summary = [ordered]@{
    approve   = 0
    reject    = 0
    escalate  = 0
    faults    = 0
    processed = 0
}

foreach ($file in $files) {
    $summary.processed++
    $repoRelative = Get-RepoRelativePath -Path $file.FullName -Root $RepoRoot
    $documentHash = Get-FileSha256 -Path $file.FullName

    # Governance Invariant 6: declined hash-lock check.
    # Applies unconditionally - DryRun must not bypass the lock.
    $lockResult = Test-DeclinedHashLock -DocumentHash $documentHash -ContextDigest $contextDigest
    if ($lockResult.Locked) {
        Write-JsonlEvent -EventType "evaluation_skipped" -Payload @{
            file_path          = $repoRelative
            document_hash      = $documentHash
            context_digest     = $contextDigest
            reason             = "declined_by_human hash-lock active"
            locking_ledger     = $lockResult.LedgerPath
            locking_timestamp  = $lockResult.ReviewerTimestamp
            locking_txn_key    = $lockResult.TransactionKey
        }
        continue
    }

    $parserCall = Invoke-JsonPython -Arguments @(
        $ParserPath,
        $file.FullName,
        "--repo-root",
        $RepoRoot
    )

    $parserJson = $null
    if ($parserCall.StdOut) {
        try {
            $parserJson = $parserCall.StdOut | ConvertFrom-Json
        }
        catch {
            $parserJson = $null
        }
    }

    if ($parserCall.ExitCode -ne 0 -or $null -eq $parserJson -or -not $parserJson.source_id) {
        $summary.faults++
        Write-JsonlEvent -EventType "operational_fault" -Payload @{
            file_path       = $repoRelative
            document_hash   = $documentHash
            context_digest  = $contextDigest
            exit_code       = 4
            fault_category  = "SYSTEM_FAULT"
            fmea_ref        = "F9"
            stderr          = $parserCall.StdErr.Trim()
            parser_error    = if ($parserJson) { [string]$parserJson.error } else { "Parser output unavailable" }
        }
        continue
    }

    $transactionKey = "{0}:{1}:{2}:{3}" -f $parserJson.source_id, $repoRelative, $documentHash, $contextDigest

    $validatorCall = Invoke-JsonPython -Arguments @(
        $ValidatorPath,
        $file.FullName,
        "--config",
        $effectiveConfigPath,
        "--repo-root",
        $RepoRoot
    )

    $resultJson = $null
    if ($validatorCall.StdOut) {
        try {
            $resultJson = $validatorCall.StdOut | ConvertFrom-Json
        }
        catch {
            $resultJson = $null
        }
    }

    if ($validatorCall.ExitCode -ge 3) {
        $summary.faults++
        $faultCategory = switch ($validatorCall.ExitCode) {
            3 { "SCHEMA_FAULT" }
            4 { "SYSTEM_FAULT" }
            5 { "TOKEN_OVERFLOW" }
            default { "SYSTEM_FAULT" }
        }

        Write-JsonlEvent -EventType "operational_fault" -Payload @{
            transaction_key = $transactionKey
            file_path       = $repoRelative
            document_hash   = $documentHash
            context_digest  = $contextDigest
            exit_code       = $validatorCall.ExitCode
            fault_category  = $faultCategory
            fmea_ref        = if ($validatorCall.ExitCode -eq 3) { "F1" } elseif ($validatorCall.ExitCode -eq 5) { "F12" } else { "F6" }
            stderr          = $validatorCall.StdErr.Trim()
        }
        continue
    }

    if ($null -eq $resultJson) {
        $summary.faults++
        Write-JsonlEvent -EventType "operational_fault" -Payload @{
            transaction_key = $transactionKey
            file_path       = $repoRelative
            document_hash   = $documentHash
            context_digest  = $contextDigest
            exit_code       = 3
            fault_category  = "SCHEMA_FAULT"
            fmea_ref        = "F1"
            stderr          = "Validator returned no structured result."
        }
        continue
    }

    $decision = [string]$resultJson.decision
    switch ($decision) {
        "approve" { $summary.approve++ }
        "reject"  { $summary.reject++ }
        "escalate" { $summary.escalate++ }
        default   { $summary.faults++ }
    }

    if (-not $DryRun) {
        if ($decision -eq "reject" -or $decision -eq "escalate") {
            New-FeedbackSidecar -ArticlePath $file.FullName -ValidationResult $resultJson
        }
        elseif (Test-Path -LiteralPath ($file.FullName + ".feedback.md")) {
            Remove-Item -LiteralPath ($file.FullName + ".feedback.md") -Force -ErrorAction SilentlyContinue
        }

        $ledgerPath = Write-LedgerEntry -Entry @{
            transaction_key         = $transactionKey
            source_id               = [string]$parserJson.source_id
            repo_relative_path      = $repoRelative
            document_hash           = $documentHash
            context_digest          = $contextDigest
            exit_code               = $validatorCall.ExitCode
            decision                = $decision
            full_model_output       = $resultJson
            model_config_snapshot   = $effectiveConfigObject
            schema_validated_result = $resultJson
            reviewer_outcome        = $null
            reviewer_timestamp      = $null
            article_token_count     = $null
            created_utc             = (Get-Date).ToUniversalTime().ToString("o")
        }

        # Promotion gate: only attempt when decision is approve.
        # Placed after ledger write so the approval is durably recorded
        # regardless of promotion outcome.
        if ($decision -eq "approve") {
            try {
                & $PromoteScriptPath -ArticlePath $file.FullName -RepoRoot $RepoRoot -StateRoot $StateRoot -ProvisionalRoot $ProvisionalRoot -VerifiedRoot $VerifiedRoot -ContextDigest $contextDigest
            }
            catch {
                $summary.faults++
                Write-JsonlEvent -EventType "operational_fault" -Payload @{
                    transaction_key  = $transactionKey
                    file_path        = $repoRelative
                    document_hash    = $documentHash
                    context_digest   = $contextDigest
                    fault_category   = "SYSTEM_FAULT"
                    fmea_ref         = "F7"
                    message          = "promotion_gated_pending_remote_wiring"
                    promotion_error  = $_.Exception.Message
                }
            }
        }
    }
    else {
        $ledgerPath = "dry-run"
    }

    Write-JsonlEvent -EventType "evaluation_completed" -Payload @{
        transaction_key = $transactionKey
        file_path       = $repoRelative
        document_hash   = $documentHash
        context_digest  = $contextDigest
        decision        = $decision
        confidence      = $resultJson.confidence
        exit_code       = $validatorCall.ExitCode
        ledger_path     = $ledgerPath
    }
}

Write-JsonlEvent -EventType "run_completed" -Payload @{
    context_digest = $contextDigest
    summary        = $summary
    dry_run        = [bool]$DryRun
}

Write-Host ("Run complete. approve={0} reject={1} escalate={2} faults={3} processed={4}" -f `
    $summary.approve, $summary.reject, $summary.escalate, $summary.faults, $summary.processed)

if ($effectiveConfigPath -and (Test-Path -LiteralPath $effectiveConfigPath)) {
    Remove-Item -LiteralPath $effectiveConfigPath -Force -ErrorAction SilentlyContinue
}
