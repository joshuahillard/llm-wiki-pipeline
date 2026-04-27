[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArticlePath,
    [string]$RepoRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$StateRoot = "C:\llm-wiki-state",
    [string]$ProvisionalRoot = $null,
    [string]$VerifiedRoot = $null,
    [string]$ContextDigest = $null,
    [switch]$DryRun,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PipelineRoot = $PSScriptRoot
if (-not $ProvisionalRoot) {
    $ProvisionalRoot = Join-Path $PipelineRoot "provisional"
}
if (-not $VerifiedRoot) {
    $VerifiedRoot = Join-Path $PipelineRoot "verified"
}
$ParserPath = Join-Path $PipelineRoot "parse_identity.py"
$AuditRoot = Join-Path $StateRoot "audit"
$PythonExe = "python"

function Ensure-Directory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
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

function Get-VerifiedDestination {
    param([string]$SourcePath)

    $sourceFull = [System.IO.Path]::GetFullPath($SourcePath)
    $provisionalFull = [System.IO.Path]::GetFullPath($ProvisionalRoot)

    if (-not $provisionalFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $provisionalFull = $provisionalFull + [System.IO.Path]::DirectorySeparatorChar
    }

    if (-not $sourceFull.StartsWith($provisionalFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "ArticlePath must live under provisional/: $SourcePath"
    }

    $relative = $sourceFull.Substring($provisionalFull.Length)
    return Join-Path $VerifiedRoot $relative
}

function Get-FileSha256 {
    param([string]$Path)

    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
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

function Get-TreeFingerprint {
    param([string]$Path)

    $root = [System.IO.Path]::GetFullPath($Path)
    $items = Get-ChildItem -LiteralPath $root -Recurse -File | Sort-Object FullName
    $material = foreach ($item in $items) {
        "{0}:{1}" -f ($item.FullName.Substring($root.Length).Replace('\', '/')), (Get-FileSha256 -Path $item.FullName)
    }

    if (-not $material) {
        return "empty-tree"
    }

    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($material -join "`n"))
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($bytes)
    }
    finally {
        $sha.Dispose()
    }

    return ([System.BitConverter]::ToString($hashBytes)).Replace('-', '').ToLowerInvariant()
}

# ---------------------------------------------------------------------------
# Gitea Client Layer
# ---------------------------------------------------------------------------
# Env-driven configuration.  All values fail-closed when absent.
# GITEA_URL        : Base URL of the Gitea instance (e.g. https://gitea.example.com)
# GITEA_TOKEN      : Personal access token with repo scope
# GITEA_REPO_OWNER : Repository owner (org or user)
# GITEA_REPO_NAME  : Repository name
# GITEA_BASE_BRANCH: Target branch for PRs (default: main)

function Get-GiteaConfig {
    $config = [ordered]@{
        BaseUrl    = $env:GITEA_URL
        Token      = $env:GITEA_TOKEN
        RepoOwner  = $env:GITEA_REPO_OWNER
        RepoName   = $env:GITEA_REPO_NAME
        BaseBranch = if ($env:GITEA_BASE_BRANCH) { $env:GITEA_BASE_BRANCH } else { "main" }
    }

    $missing = @()
    if (-not $config.BaseUrl)   { $missing += "GITEA_URL" }
    if (-not $config.Token)     { $missing += "GITEA_TOKEN" }
    if (-not $config.RepoOwner) { $missing += "GITEA_REPO_OWNER" }
    if (-not $config.RepoName)  { $missing += "GITEA_REPO_NAME" }

    return @{
        Config  = $config
        Missing = $missing
        IsValid = ($missing.Count -eq 0)
    }
}

function Invoke-GiteaApi {
    param(
        [hashtable]$GiteaConfig,
        [string]$Method,
        [string]$Endpoint,
        [object]$Body = $null
    )

    $baseUrl = $GiteaConfig.BaseUrl.TrimEnd('/')
    $uri = "{0}/api/v1/{1}" -f $baseUrl, $Endpoint.TrimStart('/')

    $headers = @{
        "Authorization" = "token $($GiteaConfig.Token)"
        "Accept"        = "application/json"
        "Content-Type"  = "application/json"
    }

    $params = @{
        Uri             = $uri
        Method          = $Method
        Headers         = $headers
        UseBasicParsing = $true
        ErrorAction     = 'Stop'
    }

    if ($Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 8)
    }

    try {
        $response = Invoke-WebRequest @params
        if ($response.Content) {
            return @{
                StatusCode = $response.StatusCode
                Data       = ($response.Content | ConvertFrom-Json)
                Raw        = $response.Content
            }
        }
        return @{
            StatusCode = $response.StatusCode
            Data       = $null
            Raw        = ""
        }
    }
    catch {
        $statusCode = 0
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        return @{
            StatusCode = $statusCode
            Data       = $null
            Raw        = $_.Exception.Message
            Error      = $true
        }
    }
}

function Get-GiteaPullRequests {
    param(
        [hashtable]$GiteaConfig,
        [string]$State = "open",
        [string]$HeadBranch = $null
    )

    $owner = $GiteaConfig.RepoOwner
    $repo  = $GiteaConfig.RepoName
    $endpoint = "repos/$owner/$repo/pulls?state=$State&limit=50"

    $result = Invoke-GiteaApi -GiteaConfig $GiteaConfig -Method GET -Endpoint $endpoint
    if ($result.Error) {
        return $result
    }

    if ($HeadBranch -and $result.Data) {
        $filtered = @($result.Data | Where-Object { $_.head.ref -eq $HeadBranch })
        $result.Data = $filtered
    }

    return $result
}

function New-GiteaPullRequest {
    param(
        [hashtable]$GiteaConfig,
        [string]$Title,
        [string]$HeadBranch,
        [string]$BodyText = ""
    )

    $owner = $GiteaConfig.RepoOwner
    $repo  = $GiteaConfig.RepoName
    $endpoint = "repos/$owner/$repo/pulls"

    $body = @{
        title = $Title
        head  = $HeadBranch
        base  = $GiteaConfig.BaseBranch
        body  = $BodyText
    }

    return Invoke-GiteaApi -GiteaConfig $GiteaConfig -Method POST -Endpoint $endpoint -Body $body
}

function Get-GiteaBranch {
    param(
        [hashtable]$GiteaConfig,
        [string]$BranchName
    )

    $owner = $GiteaConfig.RepoOwner
    $repo  = $GiteaConfig.RepoName
    $encoded = [System.Uri]::EscapeDataString($BranchName)
    $endpoint = "repos/$owner/$repo/branches/$encoded"

    return Invoke-GiteaApi -GiteaConfig $GiteaConfig -Method GET -Endpoint $endpoint
}

function Remove-GiteaBranch {
    param(
        [hashtable]$GiteaConfig,
        [string]$BranchName
    )

    $owner = $GiteaConfig.RepoOwner
    $repo  = $GiteaConfig.RepoName
    $encoded = [System.Uri]::EscapeDataString($BranchName)
    $endpoint = "repos/$owner/$repo/branches/$encoded"

    return Invoke-GiteaApi -GiteaConfig $GiteaConfig -Method DELETE -Endpoint $endpoint
}

# ---------------------------------------------------------------------------
# Declined-PR Reconciliation
# ---------------------------------------------------------------------------

function Invoke-DeclinedPrReconciliation {
    param(
        [hashtable]$GiteaConfig,
        [string]$BranchAlias,
        [string]$SourceId,
        [string]$DocumentHash,
        [string]$ContextDigest
    )

    # Query Gitea for closed, unmerged PRs targeting this branch alias.
    $closedResult = Get-GiteaPullRequests -GiteaConfig $GiteaConfig -State "closed" -HeadBranch $BranchAlias
    if ($closedResult.Error) {
        # Fail closed: if we cannot reach Gitea, we cannot confirm the PR
        # was not declined.  Return inconclusive — caller must not proceed.
        return @{
            Declined      = $false
            Inconclusive  = $true
            Error         = $closedResult.Raw
        }
    }

    # Filter to PRs that are closed AND not merged.
    $declinedPrs = @($closedResult.Data | Where-Object { -not $_.merged })
    if ($declinedPrs.Count -eq 0) {
        return @{
            Declined     = $false
            Inconclusive = $false
        }
    }

    # Conservative mapping: treat any closed+unmerged PR as a decline.
    # Capture full remote evidence for audit trail.
    $pr = $declinedPrs[0]
    $evidence = [ordered]@{
        pr_number          = $pr.number
        pr_title           = $pr.title
        pr_state           = $pr.state
        pr_merged          = $pr.merged
        pr_head_ref        = $pr.head.ref
        pr_head_sha        = $pr.head.sha
        pr_base_ref        = $pr.base.ref
        pr_user_login      = $pr.user.login
        pr_created_at      = $pr.created_at
        pr_updated_at      = $pr.updated_at
        pr_closed_at       = $pr.closed_at
        pr_merged_at       = $pr.merged_at
        pr_merge_base      = $pr.merge_base
    }

    return @{
        Declined            = $true
        Inconclusive        = $false
        Evidence            = $evidence
        ReconciliationNote  = "Conservative mapping: state=closed AND merged=false treated as declined_by_human. Source is remote Gitea PR state, not a proven human-decline fact."
    }
}

# ---------------------------------------------------------------------------
# Reconciliation Ledger Writer
# ---------------------------------------------------------------------------

function Write-ReconciliationLedgerEntry {
    param(
        [string]$SourceId,
        [string]$DocumentHash,
        [string]$ContextDigest,
        [string]$BranchAlias,
        [hashtable]$Evidence,
        [string]$ReconciliationNote
    )

    $ledgerEntry = [ordered]@{
        transaction_key       = "{0}:{1}:{2}" -f $SourceId, $DocumentHash, $ContextDigest
        source_id             = $SourceId
        document_hash         = $DocumentHash
        context_digest        = $ContextDigest
        branch_alias          = $BranchAlias
        reviewer_outcome      = "declined_by_human"
        reconciliation_source = "gitea_remote_pr_state"
        reconciliation_note   = $ReconciliationNote
        remote_evidence       = $Evidence
        reviewer_timestamp    = (Get-Date).ToUniversalTime().ToString("o")
        created_utc           = (Get-Date).ToUniversalTime().ToString("o")
    }

    $fileName = "reconciliation_" + $DocumentHash.Substring(0, 12) + "_" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffffffZ") + ".json"
    $ledgerPath = Join-Path $LedgerRoot $fileName
    Set-Content -LiteralPath $ledgerPath -Value ($ledgerEntry | ConvertTo-Json -Depth 10) -Encoding UTF8
    return $ledgerPath
}

# ---------------------------------------------------------------------------
# Remote Branch Existence Check (Fail-Closed)
# ---------------------------------------------------------------------------
# STATUS: This is a branch-existence check, NOT full tree-SHA reconciliation.
#
# P0-8 requires: "remote branch accepted only when base SHA and tree SHA
# match local intent."  To implement that fully, we need either:
#   (a) Gitea's git/trees API endpoint to retrieve the remote tree SHA, or
#   (b) a local fetch + git cat-file to compare tree objects.
#
# OQ-2 is resolved (gitea.com, enable_push=false, required_approvals=1),
# so the Gitea API surface is known.  The remaining blocker is
# implementation: wiring the git/trees call or local fetch, and comparing
# the result against the local tree fingerprint.
#
# Current behavior: if the remote branch exists, return Equivalent=$false
# unconditionally.  This is safe (fail-closed) but means that any existing
# remote branch for this alias will hard-fail the promotion, even if the
# tree actually matches.  That's correct for now — false negatives are
# acceptable, false positives are not.
#
# TODO(TD-002): Replace with actual tree-SHA comparison using Gitea
# git/trees API or local fetch + git cat-file.

function Test-RemoteBranchState {
    param(
        [hashtable]$GiteaConfig,
        [string]$BranchAlias,
        [string]$LocalTreeFingerprint
    )

    $branchResult = Get-GiteaBranch -GiteaConfig $GiteaConfig -BranchName $BranchAlias
    if ($branchResult.Error) {
        if ($branchResult.StatusCode -eq 404) {
            # Branch does not exist remotely — expected for new promotions.
            return @{
                Exists     = $false
                Equivalent = $false
                Error      = $false
            }
        }
        return @{
            Exists     = $false
            Equivalent = $false
            Error      = $true
            Message    = $branchResult.Raw
        }
    }

    $remoteSha = $branchResult.Data.commit.id
    return @{
        Exists           = $true
        Equivalent       = $false  # Fail-closed: cannot confirm without tree-SHA comparison
        RemoteCommitSha  = $remoteSha
        Error            = $false
        Note             = "Branch exists remotely. Tree-SHA equivalence check is not yet implemented (requires OQ-2). Fail-closed: treating as non-equivalent."
    }
}

# ---------------------------------------------------------------------------
# Rollback and Startup Reconciliation
# ---------------------------------------------------------------------------

function Invoke-StartupReconciliation {
    param(
        [hashtable]$GiteaConfig,
        [string]$StateRoot
    )

    $pendingRoot = Join-Path $StateRoot "pending_pr"
    if (-not (Test-Path -LiteralPath $pendingRoot)) {
        return @{ Reconciled = 0; Cleaned = 0; Errors = @() }
    }

    $pendingFiles = @(Get-ChildItem -LiteralPath $pendingRoot -Filter *.json -ErrorAction SilentlyContinue)
    $reconciled = 0
    $cleaned = 0
    $errors = @()

    foreach ($pf in $pendingFiles) {
        try {
            $pending = Get-Content -LiteralPath $pf.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            $branchAlias = [string]$pending.branch_alias

            if (-not $branchAlias) {
                $errors += "Pending entry missing branch_alias: $($pf.Name)"
                continue
            }

            # Check if the PR was merged, closed, or is still open.
            $openPrs = Get-GiteaPullRequests -GiteaConfig $GiteaConfig -State "open" -HeadBranch $branchAlias
            $closedPrs = Get-GiteaPullRequests -GiteaConfig $GiteaConfig -State "closed" -HeadBranch $branchAlias

            if ($openPrs.Error -or $closedPrs.Error) {
                $errors += "Cannot reach Gitea for branch $branchAlias — skipping reconciliation"
                continue
            }

            $hasOpenPr = ($openPrs.Data.Count -gt 0)
            $hasClosedPr = ($closedPrs.Data.Count -gt 0)

            if (-not $hasOpenPr -and -not $hasClosedPr) {
                # Orphaned pending entry: no PR exists.  Clean up the branch
                # if it still exists remotely, then remove the pending entry.
                $branchCheck = Get-GiteaBranch -GiteaConfig $GiteaConfig -BranchName $branchAlias
                if ($branchCheck.Data -and -not $branchCheck.Error) {
                    Remove-GiteaBranch -GiteaConfig $GiteaConfig -BranchName $branchAlias
                    $cleaned++
                }
                Remove-Item -LiteralPath $pf.FullName -Force -ErrorAction SilentlyContinue
                $reconciled++
            }
            elseif ($hasClosedPr -and -not $hasOpenPr) {
                # PR was closed (merged or declined).  Remove pending entry.
                Remove-Item -LiteralPath $pf.FullName -Force -ErrorAction SilentlyContinue
                $reconciled++
            }
            # If the PR is still open, leave the pending entry alone.
        }
        catch {
            $errors += "Error reconciling $($pf.Name): $($_.Exception.Message)"
        }
    }

    return @{
        Reconciled = $reconciled
        Cleaned    = $cleaned
        Errors     = $errors
    }
}

function Write-PendingPrEntry {
    param(
        [string]$StateRoot,
        [string]$BranchAlias,
        [string]$SourceId,
        [string]$DocumentHash,
        [int]$PrNumber
    )

    $pendingRoot = Join-Path $StateRoot "pending_pr"
    Ensure-Directory -Path $pendingRoot

    $entry = [ordered]@{
        branch_alias  = $BranchAlias
        source_id     = $SourceId
        document_hash = $DocumentHash
        pr_number     = $PrNumber
        created_utc   = (Get-Date).ToUniversalTime().ToString("o")
    }

    $fileName = "pending_" + $DocumentHash.Substring(0, 12) + ".json"
    $path = Join-Path $pendingRoot $fileName
    Set-Content -LiteralPath $path -Value ($entry | ConvertTo-Json -Depth 6) -Encoding UTF8
    return $path
}

# ---------------------------------------------------------------------------
# Ledger Root (shared with Run-Validator.ps1 via convention)
# ---------------------------------------------------------------------------
$LedgerRoot = Join-Path $StateRoot "ledger"

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

Ensure-Directory -Path $AuditRoot
Ensure-Directory -Path $LedgerRoot

if (-not (Test-Path -LiteralPath $ArticlePath)) {
    throw "Article not found: $ArticlePath"
}

$destinationPath = Get-VerifiedDestination -SourcePath $ArticlePath
$repoRelativeSource = Get-RepoRelativePath -Path $ArticlePath -Root $RepoRoot
$repoRelativeDestination = Get-RepoRelativePath -Path $destinationPath -Root $RepoRoot
$documentHash = Get-FileSha256 -Path $ArticlePath
$treeFingerprint = Get-TreeFingerprint -Path $PipelineRoot

$parserCall = Invoke-JsonPython -Arguments @(
    $ParserPath,
    $ArticlePath,
    "--repo-root",
    $RepoRoot
)

$sourceId = $null
if ($parserCall.ExitCode -eq 0 -and $parserCall.StdOut) {
    try {
        $parserJson = $parserCall.StdOut | ConvertFrom-Json
        $sourceId = [string]$parserJson.source_id
    }
    catch {
        $sourceId = $null
    }
}

if (-not $sourceId) {
    throw "Unable to derive source_id from parser output. Promotion must not proceed without canonical identity."
}

$branchAlias = "auto/{0}/{1}" -f $sourceId, $documentHash.Substring(0, 8)
$preview = [ordered]@{
    source_id                  = $sourceId
    source_path                = $repoRelativeSource
    destination_path           = $repoRelativeDestination
    document_hash              = $documentHash
    branch_alias               = $branchAlias
    local_tree_fingerprint     = $treeFingerprint
    pr_gated_required          = $true
    tree_sha_equivalence_rule  = "remote branch accepted only when base SHA and tree SHA match local intent"
    declined_pr_rule           = "state=closed AND merged=false routes to declined_by_human and blocks re-promotion until hash or digest changes"
    generated_utc              = (Get-Date).ToUniversalTime().ToString("o")
}

$auditFile = Join-Path $AuditRoot ("promotion-preview-" + $documentHash.Substring(0, 12) + ".json")
Set-Content -LiteralPath $auditFile -Value ($preview | ConvertTo-Json -Depth 8) -Encoding UTF8

if ($DryRun) {
    Write-Host "Promotion preview written to $auditFile"
    Write-Host "Source:      $repoRelativeSource"
    Write-Host "Destination: $repoRelativeDestination"
    Write-Host "Branch:      $branchAlias"
    exit 0
}

# ---------------------------------------------------------------------------
# Gitea Integration Gate
# ---------------------------------------------------------------------------
# Resolve Gitea config.  If env vars are missing, fail closed.
$giteaEnv = Get-GiteaConfig

if (-not $giteaEnv.IsValid) {
    $missingVars = $giteaEnv.Missing -join ", "
    throw @"
Promote-ToVerified.ps1: Gitea credentials not configured.

Missing environment variables: $missingVars

The promotion preview was computed successfully (audit: $auditFile),
but live PR creation requires GITEA_URL, GITEA_TOKEN, GITEA_REPO_OWNER,
and GITEA_REPO_NAME to be set.

Use -DryRun for preflight until Gitea credentials are available.
"@
}

$giteaConfig = $giteaEnv.Config

# ---------------------------------------------------------------------------
# Step 0: Startup Reconciliation (Preflight Cleanup)
# ---------------------------------------------------------------------------
# Clean orphaned pending_pr entries and stale remote branches before
# attempting any new promotion.  This is idempotent and safe to run
# on every invocation.
#
# STATUS: This handles preflight state cleanup only.  Full workspace
# rollback for live promotion side effects (e.g., reverting a partial
# git push) is not yet implemented because the live push path is still
# gated behind OQ-2.  When the OQ-2 gate is removed, this function
# will need to be extended to handle rollback of incomplete pushes
# and partial PR creation.
$startupResult = Invoke-StartupReconciliation -GiteaConfig $giteaConfig -StateRoot $StateRoot
if ($startupResult.Errors.Count -gt 0) {
    Write-Warning "Startup reconciliation encountered non-fatal errors:"
    foreach ($err in $startupResult.Errors) {
        Write-Warning "  $err"
    }
}

# ---------------------------------------------------------------------------
# Step 1: Declined-PR Reconciliation
# ---------------------------------------------------------------------------
# Before creating a new PR, check whether a previous PR for this branch
# was declined (closed without merging).  If so, write a conservative
# reconciliation entry to the ledger and abort.
# The context digest must match what Run-Validator.ps1 writes to the ledger
# (composite digest: script hashes + model config + origin/main marker).
# When called from Run-Validator.ps1, this is passed via -ContextDigest.
# When called standalone without -ContextDigest, fail closed: we cannot
# write a reconciliation entry that the hash-lock check will ever match.
if (-not $ContextDigest) {
    throw @"
Promote-ToVerified.ps1: -ContextDigest is required for live promotion.

The composite context digest from Run-Validator.ps1 must be passed so that
declined-PR reconciliation ledger entries match the hash-lock check in
Test-DeclinedHashLock.  Without it, reconciliation entries would be written
with an incompatible digest and silently fail to block re-promotion.

Use -DryRun for preflight (which does not require -ContextDigest).
"@
}
$contextDigest = $ContextDigest
$declineResult = Invoke-DeclinedPrReconciliation `
    -GiteaConfig $giteaConfig `
    -BranchAlias $branchAlias `
    -SourceId $sourceId `
    -DocumentHash $documentHash `
    -ContextDigest $contextDigest

if ($declineResult.Inconclusive) {
    throw @"
Promote-ToVerified.ps1: Cannot determine declined-PR status (Gitea unreachable).

Fail-closed: promotion aborted because remote PR state could not be verified.
Error: $($declineResult.Error)
Audit preview: $auditFile
"@
}

if ($declineResult.Declined) {
    $reconLedgerPath = Write-ReconciliationLedgerEntry `
        -SourceId $sourceId `
        -DocumentHash $documentHash `
        -ContextDigest $contextDigest `
        -BranchAlias $branchAlias `
        -Evidence $declineResult.Evidence `
        -ReconciliationNote $declineResult.ReconciliationNote

    throw @"
Promote-ToVerified.ps1: Declined PR detected for branch $branchAlias.

A previous PR was closed without merging.  Conservative reconciliation has
recorded this as declined_by_human in the ledger.  Re-promotion is blocked
until the document hash or context digest changes.

Reconciliation ledger entry: $reconLedgerPath
Reconciliation source: gitea_remote_pr_state
Audit preview: $auditFile
"@
}

# ---------------------------------------------------------------------------
# Step 2: Remote Branch State Check (Fail-Closed)
# ---------------------------------------------------------------------------
# Check whether the remote branch already exists.  Full tree-SHA equivalence
# (P0-8) is not yet implemented — see Test-RemoteBranchState comments.
# Current behavior: any existing remote branch blocks promotion unless an
# open PR already exists for it.
$treeCheck = Test-RemoteBranchState -GiteaConfig $giteaConfig -BranchAlias $branchAlias -LocalTreeFingerprint $treeFingerprint

if ($treeCheck.Error) {
    throw @"
Promote-ToVerified.ps1: Cannot verify remote branch state.

Fail-closed: promotion aborted because remote branch state could not be queried.
Error: $($treeCheck.Message)
Audit preview: $auditFile
"@
}

if ($treeCheck.Exists) {
    # Branch exists remotely.  Check for an existing open PR.
    $existingPrs = Get-GiteaPullRequests -GiteaConfig $giteaConfig -State "open" -HeadBranch $branchAlias
    if (-not $existingPrs.Error -and $existingPrs.Data.Count -gt 0) {
        $existingPr = $existingPrs.Data[0]
        Write-Host "Existing open PR #$($existingPr.number) found for branch $branchAlias. Skipping duplicate creation."

        # Ensure we have a pending_pr entry for tracking.
        Write-PendingPrEntry -StateRoot $StateRoot -BranchAlias $branchAlias -SourceId $sourceId -DocumentHash $documentHash -PrNumber $existingPr.number | Out-Null
        exit 0
    }

    # Branch exists but no open PR — this is an orphaned branch.
    # The tree equivalence check is fail-closed: we cannot confirm the
    # remote tree matches local intent without a full tree comparison.
    # Hard-fail per P0-8.
    throw @"
Promote-ToVerified.ps1: Remote branch $branchAlias exists but has no open PR and tree equivalence cannot be confirmed.

$($treeCheck.Note)

Fail-closed per P0-8: remote branch accepted only when base SHA and tree SHA match local intent.
Manual investigation required.  Delete the remote branch or use -Force to override.
Audit preview: $auditFile
"@
}

# ---------------------------------------------------------------------------
# Step 3: Create PR
# ---------------------------------------------------------------------------
# OQ-2 RESOLVED (Phase 1.5): Branch protection confirmed on the
# configured external Gitea instance:
#   enable_push=false, required_approvals=1, enable_force_push=false
#
# REMAINING GATE: The git-push-to-create-branch step is not yet wired.
# The pipeline needs to:
#   1. Create the branch locally with the promoted content
#   2. Push the branch to the remote
#   3. Create the PR via API
# Step 1 requires local git operations (checkout, copy file, commit) that
# interact with the working tree.  These need workspace rollback protection
# (the F7 failure mode) which is not yet implemented.
#
# The throw below stays until the local git operations and rollback are wired.

throw @"
Promote-ToVerified.ps1: Live PR creation gate — git push path not yet wired.

OQ-2 is resolved. Branch protection verified:
  enable_push=false, required_approvals=1, enable_force_push=false

All preflight checks passed:
  - Gitea credentials:  configured ($($giteaConfig.BaseUrl))
  - Startup reconciliation: $($startupResult.Reconciled) entries reconciled, $($startupResult.Cleaned) branches cleaned
  - Declined-PR check:  clear
  - Remote branch check: branch does not exist (clean slate)
  - Branch alias:       $branchAlias
  - Local fingerprint:  $treeFingerprint

Remaining before activation:
  1. Wire local git operations (branch, copy, commit, push)
  2. Implement workspace rollback for interrupted push (F7)
  3. Implement tree-SHA equivalence check (P0-8)

Audit preview: $auditFile
"@

# --- Below this line: post-gate activation code (currently unreachable) ---
# When the local git + rollback path is wired, replace the throw above
# with the following flow:
#
# $prTitle = "auto-promote: $sourceId ($($documentHash.Substring(0, 8)))"
# $prBody = @"
# Automated promotion from ``provisional/`` to ``verified/``.
#
# | Field | Value |
# |---|---|
# | source_id | $sourceId |
# | document_hash | $($documentHash.Substring(0, 8))... |
# | branch | $branchAlias |
# | tree_fingerprint | $($treeFingerprint.Substring(0, 12))... |
# | generated_utc | $(Get-Date -Format o) |
# "@
#
# $prResult = New-GiteaPullRequest -GiteaConfig $giteaConfig -Title $prTitle -HeadBranch $branchAlias -BodyText $prBody
# if ($prResult.Error) {
#     throw "PR creation failed: $($prResult.Raw)"
# }
#
# Write-PendingPrEntry -StateRoot $StateRoot -BranchAlias $branchAlias -SourceId $sourceId -DocumentHash $documentHash -PrNumber $prResult.Data.number | Out-Null
# Write-Host "PR #$($prResult.Data.number) created for $branchAlias"
# exit 0
# Write-Host "PR #$($prResult.Data.number) created for $branchAlias"
# exit 0
