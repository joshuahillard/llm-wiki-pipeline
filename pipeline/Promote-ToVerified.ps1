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
$LogRoot = Join-Path $StateRoot "logs"
$LogPath = Join-Path $LogRoot "pipeline.log"
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

    # Test-only mocks: skip live HTTP calls when LLM_WIKI_GITEA_MOCK_MODE is set.
    # Production runs must NOT set this env var.  Modes:
    #   local_only  - no remote PRs, branch not found; exercises post-local-git throw
    #                 (preserved verbatim from Phase 1.8 - promote-local depends on it)
    #   pr_success  - branch not found, PR creation succeeds with canned PSCustomObject
    #                 (used by integration stage and promote-full happy path)
    #   pr_fail     - branch not found, PR creation returns 422 error
    #                 (used by promote-full PR-fail-after-push path)
    #   push_fail   - branch not found, API behaves like pr_success but the
    #                 push itself fails inside Invoke-GitPushPromotion
    #                 (used by promote-full push-fail path)
    $mockMode = $env:LLM_WIKI_GITEA_MOCK_MODE
    if ($mockMode) {
        # existing_open_pr mode: simulate "this branch already has an open PR"
        # for the idempotent-rerun test path.  Branch lookup returns 200 +
        # branch shape; open-PR list returns 1 entry.
        if ($mockMode -eq "existing_open_pr") {
            if ($Method -eq "GET" -and $Endpoint -match "/branches/") {
                $cannedBranch = [PSCustomObject]@{
                    name   = "mocked-existing-branch"
                    commit = [PSCustomObject]@{
                        id  = "abc1234567890abcdef1234567890abcdef12345"
                        url = "<mocked>"
                    }
                }
                return @{
                    StatusCode = 200
                    Data       = $cannedBranch
                    Raw        = "<mocked-branch-exists>"
                    Error      = $false
                }
            }
            if ($Method -eq "GET" -and $Endpoint -match "/pulls\?state=open") {
                # Phase 2.1 Item 4: full consumer_required_fields shape per
                # gitea_pr_response_shape.json fixture.  Pre-Phase-2.1 this
                # canned PR was missing user, created_at, updated_at,
                # closed_at, merged_at, merge_base, and head.sha -- all of
                # which Invoke-DeclinedPrReconciliation reads.  The bug was
                # latent (mock paths never exercised the declined-PR consumer
                # against an open-PR list response), but is now fixed.
                $cannedExistingPr = [PSCustomObject]@{
                    number     = 1
                    title      = "auto-promote: existing-pr"
                    state      = "open"
                    html_url   = "$($GiteaConfig.BaseUrl.TrimEnd('/'))/$($GiteaConfig.RepoOwner)/$($GiteaConfig.RepoName)/pulls/1"
                    url        = "<mocked>"
                    head       = [PSCustomObject]@{ ref = "mocked-existing-branch"; sha = "0000000000000000000000000000000000000001" }
                    base       = [PSCustomObject]@{ ref = "main" }
                    user       = [PSCustomObject]@{ login = "mocked-user" }
                    merged     = $false
                    created_at = "2026-01-01T00:00:00Z"
                    updated_at = "2026-01-01T00:00:00Z"
                    closed_at  = $null
                    merged_at  = $null
                    merge_base = "0000000000000000000000000000000000000002"
                }
                return @{
                    StatusCode = 200
                    Data       = @($cannedExistingPr)
                    Raw        = "<mocked-existing-pr-list>"
                    Error      = $false
                }
            }
            # Other endpoints fall through to the empty-list default.
            return @{ StatusCode = 200; Data = @(); Raw = "[]"; Error = $false }
        }

        # tree_match / tree_mismatch modes: simulate an "orphan branch" state
        # (branch exists remotely AND no open PR for it).  The script's main
        # flow then defers to Test-RemoteTreeEquivalence (Step 4 / P0-8), which
        # runs a REAL git fetch against the bare-repo fixture configured by
        # promote-full's _setup_bare_repo_for_tree_path helper.  The mock just
        # needs to gate the orphan path open; it does NOT influence the tree
        # comparison itself, which uses git's own object model.
        if ($mockMode -in @("tree_match", "tree_mismatch")) {
            if ($Method -eq "GET" -and $Endpoint -match "/branches/") {
                $cannedBranch = [PSCustomObject]@{
                    name   = "mocked-orphan-branch"
                    commit = [PSCustomObject]@{
                        id  = "0000000000000000000000000000000000000000"
                        url = "<mocked>"
                    }
                }
                return @{
                    StatusCode = 200
                    Data       = $cannedBranch
                    Raw        = "<mocked-orphan-branch>"
                    Error      = $false
                }
            }
            if ($Method -eq "GET" -and $Endpoint -match "/pulls\?state=open") {
                # Empty list -> no idempotent short-circuit -> orphan path triggers.
                return @{
                    StatusCode = 200
                    Data       = @()
                    Raw        = "[]"
                    Error      = $false
                }
            }
        }

        # Other modes: branch lookup returns "not found" so the orphan-branch
        # path is not exercised here.
        if ($Method -eq "GET" -and $Endpoint -match "/branches/") {
            return @{
                StatusCode = 404
                Data       = $null
                Raw        = "mock($mockMode): branch not found"
                Error      = $true
            }
        }

        # PR creation response depends on mode.
        if ($Method -eq "POST" -and $Endpoint -match "/pulls$") {
            if ($mockMode -eq "pr_fail") {
                return @{
                    StatusCode = 422
                    Data       = $null
                    Raw        = "mock(pr_fail): simulated PR creation API error"
                    Error      = $true
                }
            }
            if ($mockMode -in @("pr_success", "push_fail", "tree_match", "tree_mismatch")) {
                # Phase 2.1 Item 4: full consumer_required_fields shape per
                # gitea_pr_response_shape.json fixture.  Pre-Phase-2.1 this
                # canned PR was missing user, created_at, updated_at, closed_at,
                # merged_at, merge_base, merged, and head.sha.  Bug was latent
                # but documented in the fixture as a parity requirement.
                $headRef = if ($Body) { $Body.head } else { "" }
                $baseRef = if ($Body) { $Body.base } else { "main" }
                $cannedPr = [PSCustomObject]@{
                    number     = 1
                    title      = if ($Body) { $Body.title } else { "mocked-pr" }
                    state      = "open"
                    html_url   = "$($GiteaConfig.BaseUrl.TrimEnd('/'))/$($GiteaConfig.RepoOwner)/$($GiteaConfig.RepoName)/pulls/1"
                    url        = "<mocked>"
                    head       = [PSCustomObject]@{ ref = $headRef; sha = "0000000000000000000000000000000000000003" }
                    base       = [PSCustomObject]@{ ref = $baseRef }
                    user       = [PSCustomObject]@{ login = "mocked-user" }
                    merged     = $false
                    created_at = "2026-01-01T00:00:00Z"
                    updated_at = "2026-01-01T00:00:00Z"
                    closed_at  = $null
                    merged_at  = $null
                    merge_base = "0000000000000000000000000000000000000004"
                }
                return @{
                    StatusCode = 201
                    Data       = $cannedPr
                    Raw        = "<mocked-pr-response>"
                    Error      = $false
                }
            }
            # local_only falls through to the empty-list default (post-local-git throw fires before this anyway)
        }

        # DELETE /branches/<name> - rollback path used by pr_fail flow.
        if ($Method -eq "DELETE" -and $Endpoint -match "/branches/") {
            return @{
                StatusCode = 204
                Data       = $null
                Raw        = "mock($mockMode): branch deleted"
                Error      = $false
            }
        }

        # Default for any other call: empty list, success.
        return @{
            StatusCode = 200
            Data       = @()
            Raw        = "[]"
            Error      = $false
        }
    }

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
                Error      = $false
            }
        }
        return @{
            StatusCode = $response.StatusCode
            Data       = $null
            Raw        = ""
            Error      = $false
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

    # Skip the head-branch filter under any LLM_WIKI_GITEA_MOCK_MODE since
    # mocks already control what's returned and don't have access to the
    # dynamically-computed branch alias.  Production runs do not set this env.
    if ($HeadBranch -and $result.Data -and -not $env:LLM_WIKI_GITEA_MOCK_MODE) {
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
        [string]$StateRoot,
        [string]$RepoRoot = $null
    )

    $reconciled = 0
    $cleaned = 0
    $worktreesRemoved = 0
    $errors = @()

    $pendingRoot = Join-Path $StateRoot "pending_pr"
    if (Test-Path -LiteralPath $pendingRoot) {
        $pendingFiles = @(Get-ChildItem -LiteralPath $pendingRoot -Filter *.json -ErrorAction SilentlyContinue)
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
                    $errors += "Cannot reach Gitea for branch $branchAlias - skipping reconciliation"
                    continue
                }

                # Coerce to array - PowerShell collapses empty arrays in
                # hashtables to $null, which would crash .Count under StrictMode.
                $hasOpenPr = (@($openPrs.Data).Count -gt 0)
                $hasClosedPr = (@($closedPrs.Data).Count -gt 0)

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
    }

    # Worktree-orphan sweep (Phase 1.9, TD-002 part 2 follow-up).
    # Scan %TEMP% for llm-wiki-promote-* directories whose corresponding remote
    # branch is gone (push never happened, or branch was deleted as part of a
    # PR-fail rollback).  Conservative: only clean up worktrees with NO remote
    # branch.  Worktrees whose remote branch still exists are left alone (they
    # might be in-use by a concurrent run, or be tracked by an open PR).
    try {
        $tempBase = [System.IO.Path]::GetTempPath()
        $wtPattern = Join-Path $tempBase "llm-wiki-promote-*"
        $wtDirs = @(Get-ChildItem -Path $wtPattern -Directory -ErrorAction SilentlyContinue)
        foreach ($wt in $wtDirs) {
            try {
                $headRef = (& git -C $wt.FullName rev-parse --abbrev-ref HEAD 2>$null | Out-String).Trim()
                # Only operate on auto/* branches (our naming convention).
                # Skip detached HEAD, unparseable, or non-auto branches.
                if (-not $headRef -or $headRef -eq "HEAD" -or -not $headRef.StartsWith("auto/")) {
                    continue
                }
                $branchCheck = Get-GiteaBranch -GiteaConfig $GiteaConfig -BranchName $headRef
                # Only clean up when remote branch is confirmed absent (404).
                # Other errors are inconclusive - leave alone.
                if ($branchCheck.Error -and $branchCheck.StatusCode -eq 404) {
                    if ($RepoRoot) {
                        & git -C $RepoRoot worktree remove --force $wt.FullName 2>&1 | Out-Null
                        & git -C $RepoRoot branch -D $headRef 2>&1 | Out-Null
                    }
                    if (Invoke-RemoveDirectoryWithRetry -Path $wt.FullName) {
                        $worktreesRemoved++
                    } else {
                        $errors += "Could not remove orphan worktree: $($wt.FullName)"
                    }
                    if ($RepoRoot) {
                        & git -C $RepoRoot worktree prune 2>&1 | Out-Null
                    }
                }
            } catch {
                $errors += "Error inspecting worktree $($wt.Name): $($_.Exception.Message)"
            }
        }
    } catch {
        $errors += "Error enumerating temp worktrees: $($_.Exception.Message)"
    }

    return @{
        Reconciled       = $reconciled
        Cleaned          = $cleaned
        WorktreesRemoved = $worktreesRemoved
        Errors           = $errors
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
# Local Git Promotion (TD-002 part 1)
# ---------------------------------------------------------------------------
# Performs the local half of the promotion: create an isolated git worktree,
# copy the article from provisional/ to verified/, commit on a new branch.
# The caller's working tree is never modified - all operations live in a
# temp worktree that is left in place for the push step (TD-002 part 2).
#
# On any failure: emits a PROMOTION_LOCAL_GIT_FAILED operational_fault to
# the JSONL pipeline log, attempts cleanup of the worktree and any local
# branch we created, then re-throws.  Run-Validator.ps1's catch block emits
# the standard F7 promotion_gated_pending_remote_wiring fault on top of that.

function Write-PromotionFault {
    param(
        [string]$LogPath,
        [string]$Step,
        [string]$BranchAlias,
        [string]$SourceId,
        [string]$DocumentHash,
        [string]$Stderr,
        [string]$FaultCategory = "PROMOTION_LOCAL_GIT_FAILED",
        [hashtable]$Extra = $null
    )

    if (-not $LogPath) {
        return
    }
    try {
        $logDir = Split-Path -Parent $LogPath
        if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        $record = [ordered]@{
            timestamp_utc  = (Get-Date).ToUniversalTime().ToString("o")
            event_type     = "operational_fault"
            fault_category = $FaultCategory
            fmea_ref       = "F7"
            step           = $Step
            branch_alias   = $BranchAlias
            source_id      = $SourceId
            document_hash  = $DocumentHash
            stderr         = $Stderr
        }
        if ($Extra) {
            foreach ($key in $Extra.Keys) {
                $record[$key] = $Extra[$key]
            }
        }
        $json = $record | ConvertTo-Json -Depth 6 -Compress
        Add-Content -LiteralPath $LogPath -Value $json -Encoding UTF8
    }
    catch {
        # Logging must never crash the rollback path.
    }
}

function Write-PromotionInfo {
    # Positive INFO log line — emits an event for successful or skipped paths
    # so absence-of-fault produces evidence too (mirrors Phase 1.6 token_method).
    param(
        [string]$LogPath,
        [string]$EventType,
        [hashtable]$Payload
    )

    if (-not $LogPath) {
        return
    }
    try {
        $logDir = Split-Path -Parent $LogPath
        if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        $record = [ordered]@{
            timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
            event_type    = $EventType
        }
        if ($Payload) {
            foreach ($key in $Payload.Keys) {
                $record[$key] = $Payload[$key]
            }
        }
        $json = $record | ConvertTo-Json -Depth 6 -Compress
        Add-Content -LiteralPath $LogPath -Value $json -Encoding UTF8
    }
    catch {
        # Logging must never crash the success path.
    }
}

function Invoke-LocalGitPromotion {
    param(
        [string]$ArticleSource,
        [string]$DestinationRelative,
        [string]$BranchAlias,
        [string]$BaseBranch,
        [string]$RepoRoot,
        [string]$SourceId,
        [string]$DocumentHash,
        [string]$LogPath
    )

    $tempBase = [System.IO.Path]::GetTempPath()
    $worktreeName = "llm-wiki-promote-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 12)
    $worktreePath = Join-Path $tempBase $worktreeName

    # Pre-flight: the base branch must exist locally.  We do not fetch in
    # part 1 - that's a part 2 concern.
    & git -C $RepoRoot rev-parse --verify "$BaseBranch^{commit}" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $stderr = "Base branch '$BaseBranch' not resolvable in $RepoRoot (git rev-parse --verify exited $LASTEXITCODE)"
        Write-PromotionFault -LogPath $LogPath -Step "verify_base_branch" `
            -BranchAlias $BranchAlias -SourceId $SourceId -DocumentHash $DocumentHash `
            -Stderr $stderr
        throw "Local git promotion failed: $stderr"
    }

    # Pre-flight: refuse if branch already exists locally (fail-loudly default).
    & git -C $RepoRoot rev-parse --verify "refs/heads/$BranchAlias" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $stderr = "Local branch '$BranchAlias' already exists in $RepoRoot"
        Write-PromotionFault -LogPath $LogPath -Step "branch_already_exists" `
            -BranchAlias $BranchAlias -SourceId $SourceId -DocumentHash $DocumentHash `
            -Stderr $stderr
        throw "Local git promotion failed: $stderr. Investigate or remove the branch before retrying."
    }

    $worktreeAdded = $false
    try {
        $addOutput = & git -C $RepoRoot worktree add $worktreePath -b $BranchAlias $BaseBranch 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "git worktree add failed (exit ${LASTEXITCODE}): $($addOutput | Out-String)"
        }
        $worktreeAdded = $true

        $destAbs = Join-Path $worktreePath $DestinationRelative
        $destDir = Split-Path -Parent $destAbs
        if ($destDir -and -not (Test-Path -LiteralPath $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }

        Copy-Item -LiteralPath $ArticleSource -Destination $destAbs -Force

        $addFileOutput = & git -C $worktreePath add -- $DestinationRelative 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "git add failed (exit ${LASTEXITCODE}): $($addFileOutput | Out-String)"
        }

        $shortHash = $DocumentHash.Substring(0, 8)
        $commitMessage = "auto-promote: $SourceId ($shortHash)"
        $commitOutput = & git -C $worktreePath commit -m $commitMessage 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "git commit failed (exit ${LASTEXITCODE}): $($commitOutput | Out-String)"
        }

        $commitSha = (& git -C $worktreePath rev-parse HEAD 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $commitSha) {
            throw "git rev-parse HEAD failed in worktree (exit ${LASTEXITCODE})"
        }

        return @{
            Success      = $true
            WorktreePath = $worktreePath
            CommitSha    = $commitSha
            BranchAlias  = $BranchAlias
        }
    }
    catch {
        $errMessage = $_.Exception.Message

        # Best-effort rollback: remove the worktree and the branch we created.
        if ($worktreeAdded) {
            & git -C $RepoRoot worktree remove --force $worktreePath 2>&1 | Out-Null
            & git -C $RepoRoot branch -D $BranchAlias 2>&1 | Out-Null
        }
        if (Test-Path -LiteralPath $worktreePath) {
            Remove-Item -LiteralPath $worktreePath -Recurse -Force -ErrorAction SilentlyContinue
        }

        Write-PromotionFault -LogPath $LogPath -Step "local_git_promotion" `
            -BranchAlias $BranchAlias -SourceId $SourceId -DocumentHash $DocumentHash `
            -Stderr $errMessage

        throw "Invoke-LocalGitPromotion failed: $errMessage"
    }
}

# ---------------------------------------------------------------------------
# Git Push Promotion (TD-002 part 2)
# ---------------------------------------------------------------------------
# Pushes the committed branch from the local worktree to the remote Gitea.
# Uses a one-shot token-bearing URL passed directly to git push (not via
# `git remote add`), so the token never lands in the worktree's .git/config.
# After push, performs a defensive sweep to verify the token did not leak.
#
# On failure: emits PROMOTION_PUSH_FAILED to JSONL, attempts cleanup of the
# worktree and any local branch we created, then re-throws with a sanitized
# message.  Run-Validator.ps1's catch block emits the standard F7
# promotion_gated_pending_remote_wiring fault on top of that.

function Invoke-RemoveDirectoryWithRetry {
    # Windows file-handle race mitigation (Phase 1.8 known issue): git child
    # processes occasionally still hold packfile handles when we try to remove
    # a worktree.  Retry up to 3 times with 200ms backoff.
    param(
        [string]$Path,
        [int]$MaxAttempts = 3,
        [int]$DelayMs = 200
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $true
    }

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            return $true
        }
        catch {
            if ($attempt -eq $MaxAttempts) {
                return $false
            }
            Start-Sleep -Milliseconds $DelayMs
        }
    }
    return $false
}

function Get-GiteaPushUrl {
    # Builds a token-bearing URL for one-shot git push.  Returns both the
    # actual URL (containing the token) and a redacted variant for any place
    # the URL might end up in logs or error output.
    param([hashtable]$GiteaConfig)

    $baseUrl = $GiteaConfig.BaseUrl.TrimEnd('/')
    if ($baseUrl -match '^(https?)://(.+)$') {
        $protocol = $matches[1]
        $hostPath = $matches[2]
        $owner = $GiteaConfig.RepoOwner
        $repo  = $GiteaConfig.RepoName
        $token = $GiteaConfig.Token

        return @{
            ActualUrl   = "${protocol}://oauth2:${token}@${hostPath}/${owner}/${repo}.git"
            RedactedUrl = "${protocol}://oauth2:<token>@${hostPath}/${owner}/${repo}.git"
        }
    }
    if ($baseUrl -match '^file://') {
        # Test-only: file:// remote (used by promote-full tree-equivalence
        # bare-repo fixture).  No token rewrite -- file paths don't carry
        # credentials.  Production runs use http(s); this branch never fires.
        return @{
            ActualUrl   = $baseUrl
            RedactedUrl = $baseUrl
        }
    }
    throw "Get-GiteaPushUrl: GITEA_URL must start with http://, https://, or file:// (got '$baseUrl')"
}

function Test-WorktreeTokenLeak {
    # Defensive sweep: scans the worktree's .git/config for the token after
    # any operation that involved a token-bearing URL.  Returns $true if the
    # token leaked into config (which would be a bug).  We never `git remote
    # add` the URL, so this should always return $false; the sweep is
    # belt-and-suspenders.
    param(
        [string]$WorktreePath,
        [string]$Token
    )

    if (-not $Token) {
        return $false
    }
    $configPath = Join-Path $WorktreePath ".git/config"
    if (-not (Test-Path -LiteralPath $configPath)) {
        # Worktrees use gitdir pointer files, not full .git directories.
        $gitDirFile = Join-Path $WorktreePath ".git"
        if (Test-Path -LiteralPath $gitDirFile -PathType Leaf) {
            $gitDirContent = Get-Content -LiteralPath $gitDirFile -Raw -Encoding UTF8
            if ($gitDirContent -match '^gitdir:\s*(.+)$') {
                $resolvedGitDir = $matches[1].Trim()
                $configPath = Join-Path $resolvedGitDir "config"
                if (-not (Test-Path -LiteralPath $configPath)) {
                    return $false
                }
            } else {
                return $false
            }
        } else {
            return $false
        }
    }

    $configContent = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8
    if (-not $configContent) {
        return $false
    }
    return $configContent.Contains($Token)
}

function Invoke-GitPushPromotion {
    param(
        [string]$WorktreePath,
        [string]$BranchAlias,
        [hashtable]$GiteaConfig,
        [string]$RepoRoot,
        [string]$LogPath,
        [string]$SourceId,
        [string]$DocumentHash
    )

    $token = $GiteaConfig.Token
    $mockMode = $env:LLM_WIKI_GITEA_MOCK_MODE
    # Defensive init for the URL vars - the catch block references $redactedUrl,
    # so under Set-StrictMode -Version Latest an undefined value would throw
    # before the fault could be logged.
    $pushUrl = $null
    $redactedUrl = "<not-set>"

    try {
        # Test-only mock branches.  Production runs do not set LLM_WIKI_GITEA_MOCK_MODE.
        if ($mockMode -eq "push_fail") {
            throw "Simulated push failure (LLM_WIKI_GITEA_MOCK_MODE=push_fail)"
        }
        if ($mockMode -in @("pr_success", "pr_fail")) {
            # Skip the actual push - no real remote in test environments.
            $mockedSha = (& git -C $WorktreePath rev-parse HEAD 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -ne 0 -or -not $mockedSha) {
                throw "git rev-parse HEAD failed in worktree (exit ${LASTEXITCODE})"
            }
            Write-PromotionInfo -LogPath $LogPath -EventType "promotion_push_completed" -Payload @{
                branch_alias  = $BranchAlias
                pushed_sha    = $mockedSha
                source_id     = $SourceId
                document_hash = $DocumentHash
                push_target   = "<mocked>"
                mocked        = $true
                mock_mode     = $mockMode
            }
            return @{
                Success      = $true
                PushedSha    = $mockedSha
                PushedBranch = $BranchAlias
            }
        }

        # Real push path.
        $urlPair = Get-GiteaPushUrl -GiteaConfig $GiteaConfig
        $pushUrl = $urlPair.ActualUrl
        $redactedUrl = $urlPair.RedactedUrl

        # Push the branch using the one-shot URL.  The URL is passed directly
        # to git push as a command-line arg; we never `git remote add` it.
        $pushOutput = & git -C $WorktreePath push $pushUrl $BranchAlias 2>&1
        $pushExit = $LASTEXITCODE
        # Sanitize output before any handling - the token must never reach a log.
        $rawOutput = ($pushOutput | Out-String)
        $sanitizedOutput = if ($token) { $rawOutput.Replace($token, '<token>') } else { $rawOutput }

        if ($pushExit -ne 0) {
            throw "git push failed (exit ${pushExit}): $sanitizedOutput"
        }

        # Resolve the pushed commit SHA from the worktree's HEAD.
        $pushedSha = (& git -C $WorktreePath rev-parse HEAD 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $pushedSha) {
            throw "git rev-parse HEAD failed in worktree (exit ${LASTEXITCODE})"
        }

        # Defensive token-leak sweep - belt-and-suspenders.
        if (Test-WorktreeTokenLeak -WorktreePath $WorktreePath -Token $token) {
            throw "DEFENSE: token leaked into worktree's .git/config after push. This indicates an upstream bug in git or in the URL-building helper. Aborting before any further side effects."
        }

        # Positive INFO log line for evidence symmetry.
        Write-PromotionInfo -LogPath $LogPath -EventType "promotion_push_completed" -Payload @{
            branch_alias    = $BranchAlias
            pushed_sha      = $pushedSha
            source_id       = $SourceId
            document_hash   = $DocumentHash
            push_target     = $redactedUrl
        }

        # Null out the token-bearing URL before returning.
        $pushUrl = $null

        return @{
            Success      = $true
            PushedSha    = $pushedSha
            PushedBranch = $BranchAlias
        }
    }
    catch {
        $errMessage = $_.Exception.Message
        # Final sanitization barrier - if the token snuck into the message,
        # redact it before logging or throwing.
        $sanitized = if ($token) { $errMessage.Replace($token, '<token>') } else { $errMessage }

        # Best-effort rollback: remove worktree and local branch.
        $worktreeRemoved = $false
        try {
            & git -C $RepoRoot worktree remove --force $WorktreePath 2>&1 | Out-Null
            $worktreeRemoved = $true
        } catch { }
        if (-not $worktreeRemoved -or (Test-Path -LiteralPath $WorktreePath)) {
            Invoke-RemoveDirectoryWithRetry -Path $WorktreePath | Out-Null
        }
        try {
            & git -C $RepoRoot branch -D $BranchAlias 2>&1 | Out-Null
        } catch { }

        # Null out the token-bearing URL before logging the fault.
        $pushUrl = $null

        Write-PromotionFault -LogPath $LogPath -Step "git_push_promotion" `
            -BranchAlias $BranchAlias -SourceId $SourceId -DocumentHash $DocumentHash `
            -Stderr $sanitized -FaultCategory "PROMOTION_PUSH_FAILED" `
            -Extra @{ push_target = $redactedUrl }

        throw "Invoke-GitPushPromotion failed: $sanitized"
    }
}

# ---------------------------------------------------------------------------
# Tree-SHA Equivalence Check (P0-8) — TD-002 part 2
# ---------------------------------------------------------------------------
# Compares the remote branch's tree and parent SHAs against the local commit
# from Invoke-LocalGitPromotion.  Equivalence = trees identical AND parents
# identical (interpretation 1 of P0-8: same tree, same base).
#
# Implementation: Option B (git fetch + rev-parse).  Uses git's own object
# model for SHA computation — no reimplementation of git blob hashing in
# PowerShell.  Fetches the remote branch into a unique temp ref under
# refs/llm-wiki/tree-compare-<guid>, computes tree SHAs and parent SHAs,
# then deletes the temp ref in finally.
#
# Returns @{ Equivalent=bool; Error=bool; Message=str; LocalTreeSha=str;
# RemoteTreeSha=str; LocalParentSha=str; RemoteParentSha=str; TreesMatch=bool;
# ParentsMatch=bool }.  Fail-closed on any error (Equivalent=$false).

function Test-RemoteTreeEquivalence {
    param(
        [hashtable]$GiteaConfig,
        [string]$BranchAlias,
        [string]$RepoRoot,
        [string]$LocalCommitSha,
        [string]$LogPath,
        [string]$SourceId,
        [string]$DocumentHash
    )

    $tempRefName = "refs/llm-wiki/tree-compare-" + [System.Guid]::NewGuid().ToString("N").Substring(0, 12)
    $token = $GiteaConfig.Token
    $urlPair = Get-GiteaPushUrl -GiteaConfig $GiteaConfig
    $fetchUrl = $urlPair.ActualUrl
    $redactedUrl = $urlPair.RedactedUrl

    $result = @{
        Equivalent       = $false
        Error            = $true
        Message          = $null
        LocalTreeSha     = $null
        RemoteTreeSha    = $null
        LocalParentSha   = $null
        RemoteParentSha  = $null
        TreesMatch       = $false
        ParentsMatch     = $false
    }

    try {
        # Fetch the remote branch into a unique temp ref.  The token-bearing
        # URL is passed directly to git fetch as an arg; we never persist it.
        $fetchOutput = & git -C $RepoRoot fetch $fetchUrl "${BranchAlias}:${tempRefName}" 2>&1
        $fetchExit = $LASTEXITCODE
        $rawFetchOutput = ($fetchOutput | Out-String)
        $sanitizedFetchOutput = if ($token) { $rawFetchOutput.Replace($token, '<token>') } else { $rawFetchOutput }

        if ($fetchExit -ne 0) {
            $result.Message = "git fetch failed (exit ${fetchExit}): $sanitizedFetchOutput"
            return $result
        }

        # Resolve local + remote tree SHAs and parent SHAs.
        $localTreeSha = (& git -C $RepoRoot rev-parse "${LocalCommitSha}^{tree}" 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            $result.Message = "Cannot resolve local commit tree: $localTreeSha"
            return $result
        }

        $remoteTreeSha = (& git -C $RepoRoot rev-parse "${tempRefName}^{tree}" 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            $result.Message = "Cannot resolve remote tree: $remoteTreeSha"
            return $result
        }

        $localParentSha = (& git -C $RepoRoot rev-parse "${LocalCommitSha}^" 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            $result.Message = "Cannot resolve local commit parent: $localParentSha"
            return $result
        }

        $remoteParentSha = (& git -C $RepoRoot rev-parse "${tempRefName}^" 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            $result.Message = "Cannot resolve remote commit parent: $remoteParentSha"
            return $result
        }

        $treesMatch   = ($localTreeSha   -eq $remoteTreeSha)
        $parentsMatch = ($localParentSha -eq $remoteParentSha)
        $equivalent   = $treesMatch -and $parentsMatch

        $result.Equivalent      = $equivalent
        $result.Error           = $false
        $result.LocalTreeSha    = $localTreeSha
        $result.RemoteTreeSha   = $remoteTreeSha
        $result.LocalParentSha  = $localParentSha
        $result.RemoteParentSha = $remoteParentSha
        $result.TreesMatch      = $treesMatch
        $result.ParentsMatch    = $parentsMatch

        $outcome = if ($equivalent) { "equivalent" } else { "not_equivalent_failed_closed" }
        Write-PromotionInfo -LogPath $LogPath -EventType "tree_sha_check" -Payload @{
            branch_alias       = $BranchAlias
            source_id          = $SourceId
            document_hash      = $DocumentHash
            local_commit_sha   = $LocalCommitSha
            local_tree_sha     = $localTreeSha
            local_parent_sha   = $localParentSha
            remote_tree_sha    = $remoteTreeSha
            remote_parent_sha  = $remoteParentSha
            trees_match        = $treesMatch
            parents_match      = $parentsMatch
            equivalent         = $equivalent
            outcome            = $outcome
            fetch_target       = $redactedUrl
        }

        return $result
    }
    finally {
        # Always clean up the temp ref.
        & git -C $RepoRoot update-ref -d $tempRefName 2>&1 | Out-Null

        # Defensive token-leak sweep on RepoRoot's .git/config.
        $repoRootGitConfig = Join-Path $RepoRoot ".git/config"
        if (Test-Path -LiteralPath $repoRootGitConfig) {
            $configContent = Get-Content -LiteralPath $repoRootGitConfig -Raw -Encoding UTF8
            if ($configContent -and $token -and $configContent.Contains($token)) {
                throw "DEFENSE: token leaked into RepoRoot's .git/config after fetch. This indicates a git or URL-builder bug. Aborting."
            }
        }

        # Null out the URL.
        $fetchUrl = $null
    }
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
Ensure-Directory -Path $LogRoot

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
    local_commit_sha           = $null
    worktree_path              = $null
    pr_number                  = $null
    pr_url                     = $null
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
# Clean orphaned pending_pr entries, stale remote branches, and orphan
# worktrees from %TEMP% before attempting any new promotion.  Idempotent
# and safe to run on every invocation.
#
# Phase 1.9 / 03b extended this with the worktree-orphan sweep: any
# %TEMP%\llm-wiki-promote-* directory whose corresponding remote branch
# is gone (404) is cleaned up.  Worktrees with surviving remote branches
# are left alone (might be in-use or be tracked by an open PR).
$startupResult = Invoke-StartupReconciliation -GiteaConfig $giteaConfig -StateRoot $StateRoot -RepoRoot $RepoRoot
if ($startupResult.WorktreesRemoved -gt 0) {
    Write-Host "Startup reconciliation removed $($startupResult.WorktreesRemoved) orphan worktree(s) from %TEMP%."
}
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
# Step 2: Remote Branch State Check (existence only)
# ---------------------------------------------------------------------------
# Test-RemoteBranchState answers "does the remote branch exist?"  When it
# does AND has an open PR, we short-circuit (idempotent re-run).  When it
# exists with NO open PR, that's an orphan from a prior interrupted run -
# we defer the tree-SHA equivalence decision to Step 4 (after local-git
# produces a commit we can compare against).
$treeCheck = Test-RemoteBranchState -GiteaConfig $giteaConfig -BranchAlias $branchAlias -LocalTreeFingerprint $treeFingerprint

if ($treeCheck.Error) {
    throw @"
Promote-ToVerified.ps1: Cannot verify remote branch state.

Fail-closed: promotion aborted because remote branch state could not be queried.
Error: $($treeCheck.Message)
Audit preview: $auditFile
"@
}

$orphanBranchDeferredCheck = $false
if ($treeCheck.Exists) {
    # Branch exists remotely.  Check for an existing open PR.
    $existingPrs = Get-GiteaPullRequests -GiteaConfig $giteaConfig -State "open" -HeadBranch $branchAlias
    if (-not $existingPrs.Error -and (@($existingPrs.Data).Count -gt 0)) {
        $existingPr = $existingPrs.Data[0]
        Write-Host "Existing open PR #$($existingPr.number) found for branch $branchAlias. Skipping duplicate creation (idempotent re-run path)."

        # Ensure we have a pending_pr entry for tracking.
        Write-PendingPrEntry -StateRoot $StateRoot -BranchAlias $branchAlias -SourceId $sourceId -DocumentHash $documentHash -PrNumber $existingPr.number | Out-Null
        exit 0
    }

    # Branch exists but no open PR - orphan from a prior interrupted run.
    # Defer the tree-SHA equivalence check to Step 4 (after local-git
    # produces a commit to compare against via Option B / git fetch + rev-parse).
    Write-Host "Remote branch $branchAlias exists with no open PR. Tree-SHA equivalence check deferred to post-local-git step (P0-8 recovery path)."
    $orphanBranchDeferredCheck = $true
}

# ---------------------------------------------------------------------------
# Step 3: Local Git Promotion (TD-002 part 1)
# ---------------------------------------------------------------------------
# Create an isolated git worktree, copy the article from provisional/ to
# verified/, and commit on the deterministic branch alias.  The user's
# working tree is never touched.  The worktree is left in place on success
# so the push step (TD-002 part 2) has a checkout to push from.

$localGitResult = Invoke-LocalGitPromotion `
    -ArticleSource $ArticlePath `
    -DestinationRelative $repoRelativeDestination `
    -BranchAlias $branchAlias `
    -BaseBranch $giteaConfig.BaseBranch `
    -RepoRoot $RepoRoot `
    -SourceId $sourceId `
    -DocumentHash $documentHash `
    -LogPath $LogPath

# Update the audit preview with the populated local-git fields and rewrite.
$preview['local_commit_sha'] = $localGitResult.CommitSha
$preview['worktree_path']    = $localGitResult.WorktreePath
Set-Content -LiteralPath $auditFile -Value ($preview | ConvertTo-Json -Depth 8) -Encoding UTF8

# ---------------------------------------------------------------------------
# Test-only boundary guard: LLM_WIKI_GITEA_MOCK_MODE=local_only
# ---------------------------------------------------------------------------
# When LLM_WIKI_GITEA_MOCK_MODE=local_only is set, throw post-local-git with
# the Phase 1.8-compatible gating message.  This preserves the promote-local
# stage contract (exercise local-git only; do not touch push or PR creation)
# now that 03b has wired the post-local-git steps.
# Production runs do NOT set LLM_WIKI_GITEA_MOCK_MODE.
if ($env:LLM_WIKI_GITEA_MOCK_MODE -eq "local_only") {
    $shortLG = $localGitResult.CommitSha.Substring(0, 8)
    throw @"
promotion_gated_pending_remote_wiring

[local_only mock] Local git promotion complete (branch=$branchAlias, commit=$shortLG, worktree=$($localGitResult.WorktreePath)); push deliberately not exercised under LLM_WIKI_GITEA_MOCK_MODE=local_only.

This mock mode bounds the test surface to local-git only.  Production runs do not set LLM_WIKI_GITEA_MOCK_MODE; full push + PR creation runs in those.

Audit preview: $auditFile

(TD-002 part 2 push path is wired and active when this mock is unset.)
"@
}

# ---------------------------------------------------------------------------
# Step 4: Tree-SHA Equivalence Check (orphan-branch recovery, P0-8)
# ---------------------------------------------------------------------------
# When Step 2 detected an orphan branch (exists, no open PR), verify its
# tree state is byte-equivalent to what we just committed locally.  Option B:
# git fetch the remote branch into a temp ref and compare tree + parent SHAs.
#   Equivalent => skip push (already there), proceed to PR creation.
#   Not equivalent or check error => rollback worktree+branch, fail closed.

$skipPush = $false
if ($orphanBranchDeferredCheck) {
    $eqCheck = Test-RemoteTreeEquivalence `
        -GiteaConfig $giteaConfig `
        -BranchAlias $branchAlias `
        -RepoRoot $RepoRoot `
        -LocalCommitSha $localGitResult.CommitSha `
        -LogPath $LogPath `
        -SourceId $sourceId `
        -DocumentHash $documentHash

    if ($eqCheck.Error) {
        & git -C $RepoRoot worktree remove --force $localGitResult.WorktreePath 2>&1 | Out-Null
        Invoke-RemoveDirectoryWithRetry -Path $localGitResult.WorktreePath | Out-Null
        & git -C $RepoRoot branch -D $branchAlias 2>&1 | Out-Null

        throw @"
Promote-ToVerified.ps1: Tree-SHA equivalence check could not run for branch $branchAlias.

$($eqCheck.Message)

Fail-closed per P0-8: cannot confirm remote tree state.
Audit preview: $auditFile
"@
    }

    if (-not $eqCheck.Equivalent) {
        & git -C $RepoRoot worktree remove --force $localGitResult.WorktreePath 2>&1 | Out-Null
        Invoke-RemoveDirectoryWithRetry -Path $localGitResult.WorktreePath | Out-Null
        & git -C $RepoRoot branch -D $branchAlias 2>&1 | Out-Null

        $treesMatch = $eqCheck.TreesMatch
        $parentsMatch = $eqCheck.ParentsMatch
        throw @"
Promote-ToVerified.ps1: Remote branch $branchAlias exists with non-equivalent tree state.

Local tree SHA:    $($eqCheck.LocalTreeSha)
Remote tree SHA:   $($eqCheck.RemoteTreeSha)
Trees match:       $treesMatch
Local parent SHA:  $($eqCheck.LocalParentSha)
Remote parent SHA: $($eqCheck.RemoteParentSha)
Parents match:     $parentsMatch

Fail-closed per P0-8: remote branch accepted only when base SHA and tree SHA match local intent.
Manual investigation required.  Delete the remote branch or use -Force to override.
Audit preview: $auditFile
"@
    }

    Write-Host "Remote branch $branchAlias is tree-equivalent to local intent (recovery from prior interrupted run). Skipping push; proceeding to PR creation."
    $skipPush = $true
}

# ---------------------------------------------------------------------------
# Step 5: Push (skipped on orphan-recovery / equivalent-tree path)
# ---------------------------------------------------------------------------

if (-not $skipPush) {
    # Invoke-GitPushPromotion handles its own rollback (worktree + branch)
    # and emits PROMOTION_PUSH_FAILED on failure; throw propagates here.
    $pushResult = Invoke-GitPushPromotion `
        -WorktreePath $localGitResult.WorktreePath `
        -BranchAlias $branchAlias `
        -GiteaConfig $giteaConfig `
        -RepoRoot $RepoRoot `
        -LogPath $LogPath `
        -SourceId $sourceId `
        -DocumentHash $documentHash
}

# ---------------------------------------------------------------------------
# Step 6: PR Creation
# ---------------------------------------------------------------------------
# After this point a remote branch exists with our intent.  PR creation is
# the next operation; on failure we MUST delete the remote branch (orphan
# would block re-promotion via the Step-2 existence check) and roll back
# the local worktree+branch.

$shortCommit = $localGitResult.CommitSha.Substring(0, 8)
$prTitle = "auto-promote: $sourceId ($shortCommit)"
$prBody = @"
Auto-promotion from LLM-Wiki content pipeline.

source_id:               $sourceId
document_hash:           $documentHash
branch_alias:            $branchAlias
local_commit_sha:        $($localGitResult.CommitSha)
local_tree_fingerprint:  $treeFingerprint
context_digest:          $contextDigest
generated_utc:           $((Get-Date).ToUniversalTime().ToString("o"))
"@

$prResult = New-GiteaPullRequest -GiteaConfig $giteaConfig -Title $prTitle -HeadBranch $branchAlias -BodyText $prBody

if ($prResult.Error) {
    # Critical: branch is on remote (push or skip-push reuse), PR creation failed.
    # Per the rollback decision tree: delete the remote branch FIRST (an orphan
    # would block re-promotion), then best-effort local cleanup, then fault.
    $branchDeleteError = $null
    try {
        $deleteResult = Remove-GiteaBranch -GiteaConfig $giteaConfig -BranchName $branchAlias
        if ($deleteResult.Error) {
            $branchDeleteError = $deleteResult.Raw
        }
    } catch {
        $branchDeleteError = $_.Exception.Message
    }

    & git -C $RepoRoot worktree remove --force $localGitResult.WorktreePath 2>&1 | Out-Null
    Invoke-RemoveDirectoryWithRetry -Path $localGitResult.WorktreePath | Out-Null
    & git -C $RepoRoot branch -D $branchAlias 2>&1 | Out-Null

    $prFaultExtra = @{ pr_create_status = $prResult.StatusCode }
    if ($branchDeleteError) {
        $prFaultExtra.branch_cleanup_error = $branchDeleteError
    }
    Write-PromotionFault -LogPath $LogPath -Step "pr_creation" `
        -BranchAlias $branchAlias -SourceId $sourceId -DocumentHash $documentHash `
        -Stderr $prResult.Raw -FaultCategory "PROMOTION_PR_FAILED" `
        -Extra $prFaultExtra

    $cleanupNote = if ($branchDeleteError) { "FAILED ($branchDeleteError)" } else { "succeeded" }
    throw @"
Promote-ToVerified.ps1: PR creation failed for branch $branchAlias.

PR API status: $($prResult.StatusCode)
PR API error:  $($prResult.Raw)
Remote branch cleanup: $cleanupNote
Audit preview: $auditFile
"@
}

$prNumber = $prResult.Data.number
$prUrl = $null
if ($prResult.Data.PSObject.Properties.Name -contains 'html_url') {
    $prUrl = $prResult.Data.html_url
}
if (-not $prUrl -and ($prResult.Data.PSObject.Properties.Name -contains 'url')) {
    $prUrl = $prResult.Data.url
}

# ---------------------------------------------------------------------------
# Step 7: Pending PR Tracking + Audit Update + Success Event
# ---------------------------------------------------------------------------
# After this point the PR exists on Gitea (durable).  Failures here are
# logged but do not roll back the PR (per the decision tree: forward, not
# back, once the PR is durable).

try {
    Write-PendingPrEntry -StateRoot $StateRoot -BranchAlias $branchAlias `
        -SourceId $sourceId -DocumentHash $documentHash -PrNumber $prNumber | Out-Null
} catch {
    Write-PromotionFault -LogPath $LogPath -Step "pending_pr_write" `
        -BranchAlias $branchAlias -SourceId $sourceId -DocumentHash $documentHash `
        -Stderr $_.Exception.Message -FaultCategory "PENDING_PR_WRITE_FAILED"
    Write-Warning "Pending PR write failed but PR #$prNumber is durable on Gitea. Startup reconciliation will repopulate state."
}

try {
    $preview['pr_number'] = $prNumber
    $preview['pr_url']    = $prUrl
    Set-Content -LiteralPath $auditFile -Value ($preview | ConvertTo-Json -Depth 8) -Encoding UTF8
} catch {
    Write-PromotionFault -LogPath $LogPath -Step "audit_rewrite" `
        -BranchAlias $branchAlias -SourceId $sourceId -DocumentHash $documentHash `
        -Stderr $_.Exception.Message -FaultCategory "AUDIT_REWRITE_FAILED"
    Write-Warning "Audit rewrite failed but PR #$prNumber is durable on Gitea."
}

$treeShaCheckOutcome = if ($skipPush) { "equivalent" } else { "skipped" }
Write-PromotionInfo -LogPath $LogPath -EventType "promotion_completed" -Payload @{
    branch_alias     = $branchAlias
    source_id        = $sourceId
    document_hash    = $documentHash
    commit_sha       = $localGitResult.CommitSha
    pr_number        = $prNumber
    pr_url           = $prUrl
    pushed_to_remote = (-not $skipPush)
    tree_sha_check   = $treeShaCheckOutcome
}

# Best-effort worktree cleanup on success.
& git -C $RepoRoot worktree remove --force $localGitResult.WorktreePath 2>&1 | Out-Null
Invoke-RemoveDirectoryWithRetry -Path $localGitResult.WorktreePath | Out-Null

Write-Host "Promotion complete: PR #$prNumber created for branch $branchAlias (commit $shortCommit)."
if ($prUrl) {
    Write-Host "PR URL: $prUrl"
}
Write-Host "Audit:  $auditFile"
exit 0
