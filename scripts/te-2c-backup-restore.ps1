<#
.SYNOPSIS
    TE-2C migrated-foundation backup/restore evidence mechanism. Backs up the local
    non-production PostgreSQL database, restores it into a disposable, isolated, ownership-labelled
    container, verifies the restore structurally, and cleans up -- with every cleanup step
    independently verified via an explicit success/failure/cannot-verify contract, not merely
    attempted or inferred from empty output.

.DESCRIPTION
    This is TE-2C evidence that a backup/restore MECHANISM works against the migrated
    PostgreSQL foundation (ADR-028). It is NOT a production backup strategy, and it does NOT
    establish or certify backup frequency, retention, RPO or RTO -- those remain genuine,
    still-open production parameters recorded in
    docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md.

    Source:  the running local Compose "db" service (read-only pg_dump; never mutated).
             Before anything else, this script POSITIVELY VERIFIES -SourceContainer actually
             carries the com.docker.compose.project=pbl-crm-hiring and
             com.docker.compose.service=db labels. It refuses to operate on any container that
             does not carry those exact labels, so an overridden -SourceContainer value can
             never cause this script to dump an arbitrary local container.
    Target:  a brand-new, disposable PostgreSQL 17 container with a fixed, bounded name
             (pbl-crm-hiring-te2c-restore-target), a freshly generated, throwaway password that
             is never printed and never reused anywhere else, AND a fixed ownership label
             ($script:OwnershipLabelKey = $script:OwnershipLabelValue) applied at creation time.
             The normal development database is never overwritten and never restored into.

    OWNERSHIP-LABEL-GUARDED DESTRUCTIVE ACTIONS. The fixed restore-target name alone is not
    sufficient authorization to force-remove whatever currently holds it: something else --
    another tool, a manual `docker run` typo, a stale unrelated container -- could occupy that
    exact name. Before this script ever force-removes a container named
    $script:RestoreContainerName (in the defensive pre-run cleanup AND in end-of-run cleanup), it
    inspects that container's own ownership label:
      - the container does not exist                          -> nothing to protect, proceed;
      - the container exists AND carries this tool's own       -> this script created it (in a
        exact ownership label                                     current or earlier run), safe
                                                                    to force-remove;
      - the container exists but does NOT carry that exact     -> FAIL CLOSED; refuse to remove
        label (or carries a different value)                      it; abort the exercise rather
                                                                    than risk deleting someone
                                                                    else's resource.
    -KeepArtifacts leaves the same ownership-labelled container running, so a later normal
    invocation's defensive pre-run cleanup still recognises and safely removes it.

    Quiescence, precisely scoped (do not read this as more than it is). Per-table row counts are
    captured from the source immediately before and immediately after pg_dump, as a
    CARDINALITY-DRIFT GUARD: if any table's row COUNT differs between the two snapshots, the
    exercise fails, because that is a clear sign of concurrent write activity that makes a
    before/after row-count comparison unreliable to interpret at all. This is deliberately NOT
    proof that the source was quiescent or byte-for-byte unchanged: an UPDATE that touches
    existing rows without changing row counts, or an equal-and-opposite INSERT+DELETE pair,
    changes nothing this check can see, and this script makes no claim otherwise. It is a coarse,
    cheap safety net against the specific failure mode of comparing a target against row counts
    that plainly do not match what was dumped -- not a snapshot-correspondence proof, and no
    stronger claim is made anywhere in this script's output.

    Verification then compares, per table between the restored target and the source's own
    before-dump row counts: exact row counts, the full table name set, and the Alembic current
    revision. This is STRUCTURAL/DATA-PRESENCE verification associated with a successful
    PostgreSQL logical backup taken through pg_dump's own internally-consistent transactional
    snapshot (pg_dump itself runs inside one transaction, so the dump file's contents are
    point-in-time consistent as of that transaction's start, independent of anything this script
    separately measures around it) -- it is explicitly NOT byte-for-byte or full row-content
    equivalence proof, and this script does not attempt one.

    pg_restore runs with --no-owner --no-privileges (so restoring into a differently-named role
    never needs ownership/grant statements the target role cannot satisfy) plus
    --single-transaction --exit-on-error (so any real error rolls back the entire restore and
    the command's own exit code is authoritative). ANY non-zero pg_restore exit is a hard
    failure -- it is never reinterpreted as an advisory warning.

    Cleanup verification uses an explicit three-state contract (Resolve-AbsenceVerification):
    the verification command itself succeeded AND confirmed absence (success); the verification
    command itself succeeded AND found the resource still present (failure); or the verification
    command itself failed to run cleanly, in which case absence is NEVER inferred from empty or
    missing output -- that is also treated as failure. Every artifact this script creates -- the
    source container's own temporary dump file (unique per run), the local temporary dump file,
    and the disposable restore-target container -- has an explicit owner and this explicit,
    independently verified removal. The source temp file's cleanup is attempted from `finally`
    even if backup/copy failed partway, and is never exempted by -KeepArtifacts (it is
    working-directory tidiness on a live, shared, non-disposable container, not evidence). Any
    cleanup step that cannot positively verify a safe final state makes the overall run FAIL
    (non-zero exit), even if backup/restore/verify themselves passed.

    No password is ever written to output. The source connection uses this repository's
    already-confirmed local trust authentication (127.0.0.1, no password required -- see
    docs/agent/acceptance/te-2ci-github-actions-validation-foundation-acceptance.md,
    "pg_hba.conf shows host all all 127.0.0.1/32 trust"). The target's generated password
    is used only inline via PGPASSWORD for that container's own docker exec calls and is
    never echoed.

.PARAMETER SourceContainer
    Name of the running Compose PostgreSQL container to back up from. Defaults to the
    project's documented Compose service container name. Whatever value is given, this script
    verifies it actually carries the expected pbl-crm-hiring/db Compose labels before touching
    it in any way -- see Test-SourceContainerIdentity below.

.PARAMETER SourceUser
    PostgreSQL role to connect as on the source. Defaults to the documented .env.example
    value (pbl_app), which is a public, non-secret prototype default, not a real credential.

.PARAMETER SourceDb
    Database name to back up. Defaults to the documented .env.example value
    (pbl_crm_hiring).

.PARAMETER KeepArtifacts
    Evidence-preservation switch. When set, the local backup dump file and the disposable
    restore-target container (still carrying its ownership label) are left in place after a
    successful run for manual inspection, instead of being removed and verified-absent. The
    temporary dump file inside the SOURCE container's own /tmp is always removed (and its
    removal verified) regardless, because it is working-directory tidiness on a live shared
    container, not evidence.

.PARAMETER SelfTest
    Runs a small set of dependency-free assertions against this script's safety-critical
    naming/parsing/comparison/verification guard functions (Test-SafeResourceName,
    ConvertTo-PositiveInteger, Test-PerTableCountsEqual, Resolve-AbsenceVerification) and exits,
    without touching Docker at all. Test-SourceContainerIdentity and Test-ContainerOwnership are
    NOT covered here because they inherently require Docker (docker inspect); they are exercised
    for real, against genuine and deliberately invalid/unowned containers, as part of the
    recorded execution evidence instead. No new test framework is introduced; this mirrors the
    "smallest useful check" principle already used for the CI Compose cleanup helper's
    fail-closed gates, adapted to PowerShell since this repository has no established PowerShell
    test runner.

.EXAMPLE
    .\scripts\te-2c-backup-restore.ps1

.EXAMPLE
    .\scripts\te-2c-backup-restore.ps1 -KeepArtifacts

.EXAMPLE
    .\scripts\te-2c-backup-restore.ps1 -SelfTest
#>

param(
    [string]$SourceContainer = "pbl-crm-hiring-db-1",
    [string]$SourceUser = "pbl_app",
    [string]$SourceDb = "pbl_crm_hiring",
    [switch]$KeepArtifacts,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"

# Fixed, bounded, never derived from external/unsafe input. This is the ONLY container name
# this script will ever force-remove -- and even then, only after the ownership-label check
# below confirms this script (a current or earlier run of it) actually created it.
$script:RestoreContainerName = "pbl-crm-hiring-te2c-restore-target"
$script:RestoreImage = "postgres:17"
$script:RestoreDb = "te2c_restore_target"
$script:RestoreUser = "te2c_restore"

# The fixed ownership label this script stamps on every restore-target container it creates,
# and requires to be present (with this exact value) before it will ever force-remove a
# container carrying the fixed name above. A container with the right name but the wrong (or
# missing) label is presumed NOT to belong to this script and is never touched.
$script:OwnershipLabelKey = "com.pbl-crm-hiring.te2c-backup-restore"
$script:OwnershipLabelValue = "owned"

# The only Compose project/service identity this script will ever treat as a legitimate source,
# regardless of what -SourceContainer is set to. See Test-SourceContainerIdentity below.
$script:ExpectedSourceComposeProject = "pbl-crm-hiring"
$script:ExpectedSourceComposeService = "db"

# ---------------------------------------------------------------------------------------
# Safety-critical guard functions. Kept small and pure where possible so -SelfTest can
# exercise them without Docker, and so the main flow below can trust their result
# unconditionally.
# ---------------------------------------------------------------------------------------

function Test-SafeResourceName {
    <#
        Refuses anything that is not exactly the one fixed disposable-container name this
        script is allowed to touch. This is the same "exact match, not a prefix or pattern"
        discipline scripts/ci-compose-cleanup.sh already uses for its own fail-closed gate,
        applied here to a single hard-coded name rather than a numeric-suffix pattern.
    #>
    param([string]$Name)
    return $Name -ceq $script:RestoreContainerName
}

function ConvertTo-PositiveInteger {
    <#
        Defensive numeric parsing for verification output. Returns $null (never throws) on
        anything that is not a clean non-negative integer, so a caller can fail closed on
        malformed/empty psql output instead of silently treating it as zero or crashing with
        an unhandled cast error.
    #>
    param([string]$Value)
    if ($null -eq $Value) { return $null }
    $trimmed = $Value.Trim()
    if ($trimmed -notmatch '^\d+$') { return $null }
    return [int64]$trimmed
}

function Test-PerTableCountsEqual {
    <#
        Compares two table-name -> row-count dictionaries. Returns an array of human-readable
        mismatch descriptions (empty array means equal). Treats a table present in one side but
        not the other as a mismatch too, not merely a count difference of a shared key.
    #>
    param([hashtable]$Left, [hashtable]$Right, [string]$LeftLabel = "left", [string]$RightLabel = "right")
    $mismatches = New-Object System.Collections.Generic.List[string]
    $allTables = @(@($Left.Keys) + @($Right.Keys) | Select-Object -Unique | Sort-Object)
    foreach ($table in $allTables) {
        $hasLeft = $Left.ContainsKey($table)
        $hasRight = $Right.ContainsKey($table)
        if (-not $hasLeft) {
            $mismatches.Add("table '$table' present in $RightLabel but not in $LeftLabel")
            continue
        }
        if (-not $hasRight) {
            $mismatches.Add("table '$table' present in $LeftLabel but not in $RightLabel")
            continue
        }
        if ($Left[$table] -ne $Right[$table]) {
            $mismatches.Add("table '$table': $LeftLabel=$($Left[$table]) $RightLabel=$($Right[$table])")
        }
    }
    return @($mismatches)
}

function Resolve-AbsenceVerification {
    <#
        Pure, fail-closed decision logic shared by every absence check in this script (container
        removal, source temp-file removal). Never infers absence from empty/missing output
        alone: a non-zero exit code from the verification command itself is ALWAYS a failure
        ("cannot verify"), even if the accompanying output happens to look like "absent". Absence
        is only ever reported when the verification command itself succeeded (ExitCode 0) AND its
        actual output exactly matches the one string that means "confirmed absent".

        - ExitCode 0, ActualOutput exactly equals AbsentMarker -> $true  (verified absent)
        - ExitCode 0, ActualOutput anything else                -> $false (verified present /
                                                                      unrecognised -- never guessed)
        - ExitCode non-zero, any ActualOutput                    -> $false (verification command
                                                                      itself failed; cannot confirm
                                                                      a safe final state)
    #>
    param([int]$ExitCode, [string]$AbsentMarker, [string]$ActualOutput)
    if ($ExitCode -ne 0) { return $false }
    $actual = if ($null -eq $ActualOutput) { "" } else { $ActualOutput.Trim() }
    return ($actual -ceq $AbsentMarker.Trim())
}

function New-ThrowawayPassword {
    <#
        A random, throwaway password for the disposable restore-target container only.
        Never derived from, equal to, or reused from any real credential. Never printed by
        any caller of this function.
    #>
    $chars = (48..57) + (65..90) + (97..122)
    -join (1..32 | ForEach-Object { [char]($chars | Get-Random) })
}

if ($SelfTest) {
    Write-Host "Running self-test of safety-critical guard functions (no Docker involved)..."
    $failures = New-Object System.Collections.Generic.List[string]

    if (-not (Test-SafeResourceName -Name $script:RestoreContainerName)) {
        $failures.Add("Test-SafeResourceName rejected the correct fixed name.")
    }
    foreach ($bad in @("pbl-crm-hiring-db-1", "pbl-crm-hiring-te2c-restore-target-evil", "", "pbl-crm-hiring", "PBL-CRM-HIRING-TE2C-RESTORE-TARGET")) {
        if (Test-SafeResourceName -Name $bad) {
            $failures.Add("Test-SafeResourceName incorrectly accepted '$bad'.")
        }
    }

    if ((ConvertTo-PositiveInteger -Value "42") -ne 42) { $failures.Add("ConvertTo-PositiveInteger failed on '42'.") }
    if ((ConvertTo-PositiveInteger -Value "0") -ne 0) { $failures.Add("ConvertTo-PositiveInteger failed on '0'.") }
    if ((ConvertTo-PositiveInteger -Value " 7 ") -ne 7) { $failures.Add("ConvertTo-PositiveInteger failed to trim whitespace around '7'.") }
    foreach ($bad in @("", "-1", "abc", "3.5", "1;drop table x", $null)) {
        if ($null -ne (ConvertTo-PositiveInteger -Value $bad)) {
            $failures.Add("ConvertTo-PositiveInteger incorrectly accepted '$bad'.")
        }
    }

    $equalA = @{ t1 = 5; t2 = 0 }
    $equalB = @{ t1 = 5; t2 = 0 }
    if ((Test-PerTableCountsEqual -Left $equalA -Right $equalB).Count -ne 0) {
        $failures.Add("Test-PerTableCountsEqual reported a mismatch for identical dictionaries.")
    }
    $diffCount = @{ t1 = 5; t2 = 0 }
    $diffCountOther = @{ t1 = 6; t2 = 0 }
    if ((Test-PerTableCountsEqual -Left $diffCount -Right $diffCountOther).Count -ne 1) {
        $failures.Add("Test-PerTableCountsEqual did not report exactly one mismatch for a single differing count.")
    }
    $missingTable = @{ t1 = 5 }
    $extraTable = @{ t1 = 5; t2 = 0 }
    if ((Test-PerTableCountsEqual -Left $missingTable -Right $extraTable).Count -ne 1) {
        $failures.Add("Test-PerTableCountsEqual did not report a mismatch for a table missing on one side.")
    }

    # Resolve-AbsenceVerification: the fail-closed contract itself. Exit code failure must
    # override even output that looks like a clean "absent" result.
    if ((Resolve-AbsenceVerification -ExitCode 0 -AbsentMarker "" -ActualOutput "") -ne $true) {
        $failures.Add("Resolve-AbsenceVerification: exit 0 + empty output + empty marker should be TRUE (absent).")
    }
    if ((Resolve-AbsenceVerification -ExitCode 0 -AbsentMarker "" -ActualOutput "abc123") -ne $false) {
        $failures.Add("Resolve-AbsenceVerification: exit 0 + non-empty output should be FALSE (present).")
    }
    if ((Resolve-AbsenceVerification -ExitCode 1 -AbsentMarker "" -ActualOutput "") -ne $false) {
        $failures.Add("Resolve-AbsenceVerification: non-zero exit code must be FALSE even with output that looks absent.")
    }
    if ((Resolve-AbsenceVerification -ExitCode 0 -AbsentMarker "TE2C_ABSENT" -ActualOutput "TE2C_ABSENT") -ne $true) {
        $failures.Add("Resolve-AbsenceVerification: exit 0 + matching marker should be TRUE.")
    }
    if ((Resolve-AbsenceVerification -ExitCode 0 -AbsentMarker "TE2C_ABSENT" -ActualOutput "TE2C_PRESENT") -ne $false) {
        $failures.Add("Resolve-AbsenceVerification: exit 0 + non-matching marker should be FALSE.")
    }
    if ((Resolve-AbsenceVerification -ExitCode 127 -AbsentMarker "TE2C_ABSENT" -ActualOutput "TE2C_ABSENT") -ne $false) {
        $failures.Add("Resolve-AbsenceVerification: non-zero exit code must override even a matching marker.")
    }
    if ((Resolve-AbsenceVerification -ExitCode 0 -AbsentMarker "TE2C_ABSENT" -ActualOutput "garbage") -ne $false) {
        $failures.Add("Resolve-AbsenceVerification: unrecognised output must be FALSE, never guessed TRUE.")
    }

    $pw1 = New-ThrowawayPassword
    $pw2 = New-ThrowawayPassword
    if ($pw1.Length -ne 32) { $failures.Add("New-ThrowawayPassword did not return 32 characters.") }
    if ($pw1 -ceq $pw2) { $failures.Add("New-ThrowawayPassword returned the same value twice in a row.") }

    if ($failures.Count -gt 0) {
        Write-Host ""
        Write-Error "Self-test FAILED:`n$($failures -join "`n")"
        exit 1
    }
    Write-Host "Self-test PASSED (20 assertions, no Docker used)."
    exit 0
}

# ---------------------------------------------------------------------------------------
# Docker/PostgreSQL helpers. All source-side commands connect via the local trust-auth path
# already confirmed for this repository's postgres:17 image (127.0.0.1, no password). All
# target-side commands use the throwaway password via an inline, never-printed PGPASSWORD.
# ---------------------------------------------------------------------------------------

function Test-SourceContainerIdentity {
    <#
        Positively verifies, via Docker Compose's own labels (not the container name alone),
        that $Name is actually the pbl-crm-hiring project's "db" service before this script
        touches it in any way. A container that does not exist, or does not carry both labels
        with the expected exact values, fails closed -- this script then refuses to run
        pg_dump or any source-side command at all, regardless of what -SourceContainer was set
        to.
    #>
    param([string]$Name)
    try {
        $project = docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' $Name 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        $service = docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' $Name 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
    } catch {
        return $false
    }
    return ($project.Trim() -ceq $script:ExpectedSourceComposeProject) -and ($service.Trim() -ceq $script:ExpectedSourceComposeService)
}

function Test-ContainerOwnership {
    <#
        Inspects whether a container named $Name carries THIS script's fixed ownership label
        with its exact expected value. Returns one of three strings, deliberately not a bare
        boolean, because "does not exist" and "exists but is not mine" require different
        handling by the caller:

          "ABSENT" - no container with this name exists (or it could not be inspected at all).
                     Nothing to protect; safe to proceed (there is nothing to remove).
          "OWNED"  - the container exists and carries this tool's exact ownership label. This
                     script (a current or earlier run of it) created it; safe to force-remove.
          "UNOWNED"- the container exists but does NOT carry the expected label (missing or a
                     different value). Something else created or is using this name. MUST NOT be
                     force-removed.
    #>
    param([string]$Name)
    $labelValue = docker inspect --format "{{ index .Config.Labels `"$script:OwnershipLabelKey`" }}" $Name 2>$null
    $inspectExit = $LASTEXITCODE
    if ($inspectExit -ne 0) { return "ABSENT" }
    if ($labelValue.Trim() -ceq $script:OwnershipLabelValue) { return "OWNED" }
    return "UNOWNED"
}

function Invoke-SourcePsql {
    param([string]$Sql)
    $output = docker exec $SourceContainer psql -h 127.0.0.1 -U $SourceUser -d $SourceDb -t -A -c $Sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Source query failed (exit $LASTEXITCODE): $Sql`n$output"
    }
    return $output
}

function Invoke-TargetPsql {
    param([string]$Sql, [string]$Password)
    $output = docker exec -e PGPASSWORD=$Password $script:RestoreContainerName `
        psql -h 127.0.0.1 -U $script:RestoreUser -d $script:RestoreDb -t -A -c $Sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Target query failed (exit $LASTEXITCODE): $Sql`n$output"
    }
    return $output
}

function Get-TableNames {
    param([scriptblock]$QueryFn)
    $raw = & $QueryFn "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
    return @($raw | Where-Object { $_.Trim() -ne "" } | ForEach-Object { $_.Trim() })
}

function Get-PerTableRowCounts {
    <#
        Returns a table-name -> exact-row-count hashtable (never an estimate). N+1 queries
        against a small, already-local schema is simple, easy to audit, and fast enough for a
        one-off evidence exercise; no dynamic-SQL/DO-block cleverness is introduced.
    #>
    param([scriptblock]$QueryFn, [string[]]$Tables)
    $counts = @{}
    foreach ($table in $Tables) {
        $countRaw = & $QueryFn "SELECT count(*) FROM public.""$table"";"
        $count = ConvertTo-PositiveInteger -Value $countRaw
        if ($null -eq $count) {
            throw "Could not parse a valid row count for table '$table' (got '$countRaw')."
        }
        $counts[$table] = $count
    }
    return $counts
}

function Get-RowCountTotal {
    param([hashtable]$Counts)
    $total = 0L
    foreach ($value in $Counts.Values) { $total += $value }
    return $total
}

function Get-AlembicRevision {
    param([scriptblock]$QueryFn)
    $raw = & $QueryFn "SELECT version_num FROM alembic_version;"
    $revision = $raw.Trim()
    if ($revision -eq "") {
        throw "alembic_version table returned no revision."
    }
    return $revision
}

function Remove-AndVerifyContainer {
    <#
        Ownership-guarded, independently verified container removal (findings 1 and 4 together).

        1. Refuses anything but the one fixed, safe resource name (Test-SafeResourceName).
        2. Inspects ownership (Test-ContainerOwnership) BEFORE attempting removal:
             ABSENT  -> nothing to remove; skip straight to verification (which trivially
                        confirms absence).
             UNOWNED -> FAIL CLOSED. Does not call `docker rm` at all. Returns $false.
             OWNED   -> proceeds to `docker rm --force`.
        3. Verifies the actual final state with Resolve-AbsenceVerification, which treats a
           failed verification command itself as failure -- never inferring absence from empty
           output alone.

        Returns $true only when absence is positively confirmed by a verification command that
        itself succeeded.
    #>
    param([string]$Name)
    if (-not (Test-SafeResourceName -Name $Name)) {
        throw "Internal safety check failed: refusing to remove a container name that did not pass Test-SafeResourceName."
    }

    $ownership = Test-ContainerOwnership -Name $Name
    if ($ownership -eq "UNOWNED") {
        Write-Warning "A container named '$Name' exists but does NOT carry this tool's ownership label ($script:OwnershipLabelKey=$script:OwnershipLabelValue). Refusing to remove it -- it may belong to something else. This script never force-removes a resource it does not own, even one matching its own fixed disposable name."
        return $false
    }
    if ($ownership -eq "OWNED") {
        docker rm --force $Name *>$null
        # `docker rm`'s own exit code is deliberately not trusted alone here (see the
        # Resolve-AbsenceVerification docstring): the verification query below is what decides
        # the outcome, including distinguishing "verified absent" from "the verification command
        # itself could not run".
    }
    # ABSENT falls straight through to verification, which will confirm there is nothing there.

    $stillPresent = docker ps -a -q --filter "name=^${Name}$" 2>$null
    $verifyExit = $LASTEXITCODE
    $confirmed = Resolve-AbsenceVerification -ExitCode $verifyExit -AbsentMarker "" -ActualOutput $stillPresent
    if (-not $confirmed -and $verifyExit -ne 0) {
        Write-Warning "Absence-verification command itself failed (docker ps exit $verifyExit) while checking for '$Name'; cannot confirm a safe final state."
    }
    return $confirmed
}

function Remove-AndVerifyLocalFile {
    <#
        Removes a local file and independently verifies it no longer exists via Test-Path,
        rather than assuming Remove-Item succeeded because it did not throw.
    #>
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $true }
    Remove-Item -Path $Path -Force -ErrorAction SilentlyContinue
    return -not (Test-Path $Path)
}

function Remove-AndVerifySourceTempFile {
    <#
        Removes the source container's own temporary dump file using an EXPLICIT probe contract
        with distinct markers for "present" and "absent" (finding 1B), so a generic non-zero
        `test -e` exit can never be confused with a positively confirmed "absent" result. The
        probe shell itself always exits 0 and prints exactly one recognised marker; a non-zero
        exit from `docker exec` therefore always means the probe itself could not run (container
        stopped, daemon unreachable, etc.) and is never interpreted as "file gone".
    #>
    param([string]$Container, [string]$Path)

    docker exec $Container rm -f $Path *>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not run 'rm -f' for '$Path' inside '$Container' (exit $LASTEXITCODE)."
        return $false
    }

    $probeOutput = docker exec $Container sh -c "if [ -e '$Path' ]; then echo TE2C_PRESENT; else echo TE2C_ABSENT; fi" 2>$null
    $probeExit = $LASTEXITCODE
    $marker = if ($null -eq $probeOutput) { "" } else { ($probeOutput | Select-Object -Last 1).ToString() }
    $confirmedAbsent = Resolve-AbsenceVerification -ExitCode $probeExit -AbsentMarker "TE2C_ABSENT" -ActualOutput $marker

    if (-not $confirmedAbsent) {
        if ($probeExit -ne 0) {
            Write-Warning "Absence-verification probe itself failed (docker exec exit $probeExit) for '$Path' inside '$Container'; cannot confirm a safe final state."
        } elseif ($marker.Trim() -ceq "TE2C_PRESENT") {
            Write-Warning "'$Path' inside '$Container' is still present after removal."
        } else {
            Write-Warning "Absence-verification probe returned an unrecognised marker ('$marker') for '$Path' inside '$Container'; cannot confirm a safe final state."
        }
    }
    return $confirmedAbsent
}

# ---------------------------------------------------------------------------------------
# Main exercise
# ---------------------------------------------------------------------------------------

$timings = [ordered]@{}
$totalStart = Get-Date
$restoreTargetCreated = $false
$sourceConfirmedReachable = $false
$runId = [guid]::NewGuid().ToString('N')
$tempDumpPath = Join-Path ([System.IO.Path]::GetTempPath()) "te2c-backup-restore-$runId.dump"
# Unique per run so a concurrent or previously interrupted run's source-side temp file can
# never collide with this run's.
$sourceTempPath = "/tmp/te2c-source-backup-$runId.dump"

try {
    Write-Host "=== TE-2C backup/restore evidence exercise ==="
    Write-Host "Source container (requested): $SourceContainer"
    Write-Host "Source database:  $SourceDb (user: $SourceUser)"
    Write-Host "Restore target:   $script:RestoreContainerName (disposable, fixed name, ownership-labelled, isolated)"
    Write-Host ""

    Write-Host "Verifying '$SourceContainer' is actually the pbl-crm-hiring Compose 'db' service (by label, not name alone)..."
    if (-not (Test-SourceContainerIdentity -Name $SourceContainer)) {
        throw "Refusing to operate: '$SourceContainer' does not carry com.docker.compose.project='$script:ExpectedSourceComposeProject' and com.docker.compose.service='$script:ExpectedSourceComposeService'. This script only ever backs up the confirmed pbl-crm-hiring 'db' service, never an arbitrary local container."
    }
    Write-Host "Source container identity confirmed."

    Write-Host "Confirming source database is reachable (local trust auth, no password)..."
    Invoke-SourcePsql -Sql "SELECT 1;" | Out-Null
    $sourceConfirmedReachable = $true
    Write-Host "Source reachable."

    Write-Host "Defensive pre-run cleanup: checking for any leftover restore target from an earlier interrupted run..."
    if (-not (Remove-AndVerifyContainer -Name $script:RestoreContainerName)) {
        throw "Defensive pre-run cleanup could not confirm '$script:RestoreContainerName' is safely absent (or is present but not owned by this tool). Refusing to proceed. See the warning above for the exact reason."
    }

    # --- capture source structural facts BEFORE dumping (the cardinality-drift "before" snapshot) ---
    $sourceTables = Get-TableNames -QueryFn { param($sql) Invoke-SourcePsql -Sql $sql }
    $sourceTableCount = $sourceTables.Count
    $sourceAlembicRevisionBefore = Get-AlembicRevision -QueryFn { param($sql) Invoke-SourcePsql -Sql $sql }
    $beforeCounts = Get-PerTableRowCounts -QueryFn { param($sql) Invoke-SourcePsql -Sql $sql } -Tables $sourceTables
    Write-Host "Source: $sourceTableCount table(s), Alembic revision $sourceAlembicRevisionBefore, $(Get-RowCountTotal $beforeCounts) total row(s) (pre-dump snapshot)."

    # --- backup ---
    $backupStart = Get-Date
    Write-Host ""
    Write-Host "Backing up source database (pg_dump -Fc, inside the source container, read-only)..."
    docker exec $SourceContainer pg_dump -h 127.0.0.1 -U $SourceUser -d $SourceDb -Fc -f $sourceTempPath
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed (exit $LASTEXITCODE)." }
    docker cp "${SourceContainer}:${sourceTempPath}" $tempDumpPath
    if ($LASTEXITCODE -ne 0) { throw "docker cp of the backup artifact out of the source container failed." }
    $backupSize = (Get-Item $tempDumpPath).Length
    $timings.Backup = (Get-Date) - $backupStart
    Write-Host "Backup complete: $tempDumpPath ($backupSize bytes) in $([math]::Round($timings.Backup.TotalSeconds, 2))s."

    # --- capture source structural facts AFTER dumping (the cardinality-drift "after" snapshot) ---
    Write-Host "Checking for cardinality drift during the backup window (before/after per-table row-count comparison)..."
    $sourceAlembicRevisionAfter = Get-AlembicRevision -QueryFn { param($sql) Invoke-SourcePsql -Sql $sql }
    $afterCounts = Get-PerTableRowCounts -QueryFn { param($sql) Invoke-SourcePsql -Sql $sql } -Tables $sourceTables
    $driftMismatches = Test-PerTableCountsEqual -Left $beforeCounts -Right $afterCounts -LeftLabel "before-dump" -RightLabel "after-dump"
    if ($driftMismatches.Count -gt 0 -or ($sourceAlembicRevisionAfter -cne $sourceAlembicRevisionBefore)) {
        $details = @($driftMismatches)
        if ($sourceAlembicRevisionAfter -cne $sourceAlembicRevisionBefore) {
            $details += "Alembic revision changed: before=$sourceAlembicRevisionBefore after=$sourceAlembicRevisionAfter"
        }
        throw "Cardinality drift detected between the before-dump and after-dump per-table row counts; a before/after row-count comparison is not reliable to interpret when the source changed during the backup window, so this run cannot be trusted. Drift detected:`n$($details -join "`n")"
    }
    Write-Host "No cardinality drift detected (identical per-table row counts and Alembic revision before and after pg_dump). This is a coarse drift guard, not proof the source was fully unchanged -- see this script's own header comment."
    $sourceCountsBeforeDump = $beforeCounts
    $sourceAlembicRevision = $sourceAlembicRevisionBefore

    # --- restore into a fresh, disposable, isolated, ownership-labelled target ---
    $restoreStart = Get-Date
    Write-Host ""
    Write-Host "Creating disposable restore-target container ($script:RestoreImage), labelled $script:OwnershipLabelKey=$script:OwnershipLabelValue..."
    $targetPassword = New-ThrowawayPassword
    docker run -d --name $script:RestoreContainerName --network pbl-crm-hiring_default `
        --label "$($script:OwnershipLabelKey)=$($script:OwnershipLabelValue)" `
        -e POSTGRES_DB=$script:RestoreDb -e POSTGRES_USER=$script:RestoreUser `
        -e POSTGRES_PASSWORD=$targetPassword -e TZ=UTC -e PGTZ=UTC $script:RestoreImage *>$null
    if ($LASTEXITCODE -ne 0) { throw "Failed to start the disposable restore-target container." }
    $restoreTargetCreated = $true

    Write-Host "Waiting for the restore target to accept connections..."
    $ready = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        docker exec $script:RestoreContainerName pg_isready -U $script:RestoreUser -d $script:RestoreDb *>$null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "Restore-target database did not become ready in time." }

    Write-Host "Copying the backup artifact into the restore target and running pg_restore..."
    docker cp $tempDumpPath "${script:RestoreContainerName}:/tmp/restore.dump"
    if ($LASTEXITCODE -ne 0) { throw "docker cp of the backup artifact into the restore target failed." }
    # --no-owner --no-privileges: restoring into a differently-named role never needs ownership/
    # grant statements the target role cannot satisfy, so a legitimate restore should not need
    # to tolerate any warning-level non-zero exit in the first place.
    # --single-transaction --exit-on-error: any real error rolls back the ENTIRE restore, so the
    # database ends up either fully populated or with nothing at all -- never a silently partial
    # restore -- and pg_restore's own exit code becomes authoritative.
    docker exec -e PGPASSWORD=$targetPassword $script:RestoreContainerName `
        pg_restore -h 127.0.0.1 -U $script:RestoreUser -d $script:RestoreDb `
        --no-owner --no-privileges --single-transaction --exit-on-error /tmp/restore.dump
    $restoreExit = $LASTEXITCODE
    if ($restoreExit -ne 0) {
        # No tolerate-and-warn path: any non-zero pg_restore exit is a hard failure, full stop.
        throw "pg_restore FAILED (exit $restoreExit). See its output above for the underlying error."
    }
    $timings.Restore = (Get-Date) - $restoreStart
    Write-Host "Restore step complete in $([math]::Round($timings.Restore.TotalSeconds, 2))s (pg_restore exit 0)."

    # --- verify ---
    $verifyStart = Get-Date
    Write-Host ""
    Write-Host "Verifying the restore structurally (per-table row counts, table set, Alembic revision)..."

    $targetTables = Get-TableNames -QueryFn { param($sql) Invoke-TargetPsql -Sql $sql -Password $targetPassword }
    $targetTableCount = $targetTables.Count
    $targetAlembicRevision = Get-AlembicRevision -QueryFn { param($sql) Invoke-TargetPsql -Sql $sql -Password $targetPassword }
    $targetCounts = Get-PerTableRowCounts -QueryFn { param($sql) Invoke-TargetPsql -Sql $sql -Password $targetPassword } -Tables $targetTables

    $verificationFailures = New-Object System.Collections.Generic.List[string]
    if ($targetTableCount -ne $sourceTableCount) {
        $verificationFailures.Add("Table count mismatch: source=$sourceTableCount target=$targetTableCount")
    }
    if ($targetAlembicRevision -cne $sourceAlembicRevision) {
        $verificationFailures.Add("Alembic revision mismatch: source=$sourceAlembicRevision target=$targetAlembicRevision")
    }
    $rowMismatches = Test-PerTableCountsEqual -Left $sourceCountsBeforeDump -Right $targetCounts -LeftLabel "source-before-dump" -RightLabel "restored-target"
    foreach ($mismatch in $rowMismatches) { $verificationFailures.Add("Row count $mismatch") }

    $timings.Verify = (Get-Date) - $verifyStart

    $sourceRowTotal = Get-RowCountTotal $sourceCountsBeforeDump
    $targetRowTotal = Get-RowCountTotal $targetCounts

    Write-Host ""
    Write-Host "--- Verification summary (structural/data-presence, not byte-for-byte equivalence) ---"
    Write-Host ("Table count:       source={0} target={1}" -f $sourceTableCount, $targetTableCount)
    Write-Host ("Alembic revision:  source={0} target={1}" -f $sourceAlembicRevision, $targetAlembicRevision)
    Write-Host ("Total row count:   source={0} target={1} (per-table comparison is the authoritative check, not this total)" -f $sourceRowTotal, $targetRowTotal)

    if ($verificationFailures.Count -gt 0) {
        throw "Verification FAILED:`n$($verificationFailures -join "`n")"
    }
    Write-Host "Verification PASSED: restored target's per-table row counts, table set and Alembic revision match the source's pre-dump state."

    $timings.Total = (Get-Date) - $totalStart
    Write-Host ""
    Write-Host "--- Timings ---"
    foreach ($key in $timings.Keys) {
        Write-Host ("{0,-8}: {1,6:N2}s" -f $key, $timings[$key].TotalSeconds)
    }

    Write-Host ""
    Write-Host "TE-2C backup/restore evidence exercise: PASS"
    $script:exitCode = 0
} catch {
    Write-Host ""
    Write-Error "TE-2C backup/restore evidence exercise: FAIL`n$($_.Exception.Message)"
    $script:exitCode = 1
} finally {
    Write-Host ""
    Write-Host "Cleaning up..."

    # Source container's own temporary dump file: always attempted (never exempted by
    # -KeepArtifacts) and always verified via the explicit probe contract, from finally, even if
    # backup/copy failed partway. Only skipped if we never even confirmed the source was
    # reachable, so this never execs into a container this run has not already established is
    # safe to touch.
    if ($sourceConfirmedReachable) {
        if (-not (Remove-AndVerifySourceTempFile -Container $SourceContainer -Path $sourceTempPath)) {
            Write-Warning "Could not verify removal of the source container's temporary dump file ($sourceTempPath)."
            $script:exitCode = 1
        } else {
            Write-Host "Removed and verified absence of the source container's temporary dump file."
        }
    }

    if (Test-Path $tempDumpPath) {
        if ($KeepArtifacts) {
            Write-Host "KeepArtifacts set: preserving local backup artifact at $tempDumpPath"
        } else {
            if (Remove-AndVerifyLocalFile -Path $tempDumpPath) {
                Write-Host "Removed and verified absence of the local backup artifact."
            } else {
                Write-Warning "Could not verify removal of the local backup artifact at $tempDumpPath."
                $script:exitCode = 1
            }
        }
    }

    if ($restoreTargetCreated) {
        if ($KeepArtifacts) {
            Write-Host "KeepArtifacts set: preserving disposable restore-target container '$script:RestoreContainerName' (still ownership-labelled) for manual inspection."
            Write-Host "Remove it later with: docker rm -f $script:RestoreContainerName"
        } else {
            if (Remove-AndVerifyContainer -Name $script:RestoreContainerName) {
                Write-Host "Removed and verified absence of the disposable restore-target container."
            } else {
                Write-Warning "Could not verify removal of the disposable restore-target container '$script:RestoreContainerName'."
                Write-Warning "It will be removed by this script's own defensive pre-run cleanup on the next invocation (if still ownership-labelled)."
                $script:exitCode = 1
            }
        }
    }
}

exit $script:exitCode
