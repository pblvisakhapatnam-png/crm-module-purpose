<#
.SYNOPSIS
    Slice 6P vendor-demo wrapper. Thin orchestration only -- every seed/cleanup/status
    operation is delegated to the existing TE-1 backend smoke-data harness
    (backend/tooling/smoke_data); this script never implements a second seed engine.

.DESCRIPTION
    prepare   - seeds the vendor-demo-bundle scenario and saves the active run's manifest and
                a human-readable launch sheet locally.
    status    - reports whether the active run's anchor records (Account/Opportunity/
                Commercial Offer/Work Order/Lead) still exist, without mutating anything.
    preflight - runs backend/frontend health checks plus the non-destructive
                "@demo-preflight" Playwright subset (e2e/tests/demo-preflight.spec.ts)
                against the active run. Never performs a presenter's live-mutation action.
    reset     - cleans up the current active run (if any) and prepares a fresh one.
    cleanup   - removes the active run's seeded records and the local active-run/launch-sheet
                files. Idempotent.

    Local state lives under .vendor-demo/ at the repo root (gitignored, never committed):
      .vendor-demo/active-run.json   - the seeded manifest for the currently active run
      .vendor-demo/launch-sheet.md   - generated presenter launch sheet for that run

    If no active run file exists, status/preflight/cleanup fail safely with a clear message
    rather than guessing at or broadly deleting data. prepare refuses to seed a second bundle
    on top of an already-active run; use reset or cleanup first.

.EXAMPLE
    .\scripts\vendor-demo.ps1 prepare
.EXAMPLE
    .\scripts\vendor-demo.ps1 status
.EXAMPLE
    .\scripts\vendor-demo.ps1 preflight
.EXAMPLE
    .\scripts\vendor-demo.ps1 reset
.EXAMPLE
    .\scripts\vendor-demo.ps1 cleanup
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("prepare", "status", "preflight", "reset", "cleanup")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$demoDir = Join-Path $repoRoot ".vendor-demo"
$activeRunPath = Join-Path $demoDir "active-run.json"
$launchSheetPath = Join-Path $demoDir "launch-sheet.md"
# One segment at a time, as run-e2e.ps1 does: on Linux a backslash is an ordinary filename character, so the single
# literal "e2e\.manifest" would name a file in the repository root instead of the e2e/.manifest directory.
$e2eManifestDir = Join-Path (Join-Path $repoRoot "e2e") ".manifest"
$e2eManifestPath = Join-Path $e2eManifestDir "vendor-demo.json"
$scenario = "vendor-demo-bundle"

function Wait-ForHttp {
    param([string]$Url, [int]$TimeoutSeconds = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

function Get-ActiveManifest {
    if (-not (Test-Path $activeRunPath)) { return $null }
    try {
        return Get-Content -Path $activeRunPath -Raw | ConvertFrom-Json
    } catch {
        Write-Warning "The active run file at $activeRunPath could not be parsed as JSON."
        return $null
    }
}

# Runs the backend cleanup CLI and returns its exit code. Output is explicitly captured and
# re-printed via Write-Host (not left on the success stream) so this function's `return` value
# is the exit code alone -- see scripts/smoke-data.ps1 for why a helper that mixes unsuppressed
# docker output with `return $LASTEXITCODE` silently corrupts its own return value.
function Invoke-BackendCleanup {
    param([string]$RunId)
    $output = docker compose exec -T backend python -m tooling.smoke_data cleanup --run-id $RunId 2>&1
    $exitCode = $LASTEXITCODE
    $output | ForEach-Object { Write-Host $_ }
    return $exitCode
}

function Invoke-BackendStatus {
    # -RequirePresent asks the backend for the state this wrapper actually cares about. Without it
    # `status` exits 0 both when every anchor record is present and when they have all been cleaned
    # up - two opposite states - and both call sites below read any zero as "the demo data is
    # there". A run cleaned up outside this wrapper therefore passed preflight with nothing left to
    # demonstrate (independent review, fifth pass).
    param([string]$RunId, [switch]$RequirePresent)
    if ($RequirePresent) {
        $output = docker compose exec -T backend python -m tooling.smoke_data status --run-id $RunId --require-present 2>&1
    }
    else {
        $output = docker compose exec -T backend python -m tooling.smoke_data status --run-id $RunId 2>&1
    }
    $exitCode = $LASTEXITCODE
    $output | ForEach-Object { Write-Host $_ }
    return $exitCode
}

function New-LaunchSheet {
    param($Manifest)

    $lines = New-Object System.Collections.Generic.List[string]
    [void]$lines.Add("# Vendor Demo Launch Sheet")
    [void]$lines.Add("")
    [void]$lines.Add("Generated locally by ``scripts\vendor-demo.ps1 prepare``. This file is not committed to source control.")
    [void]$lines.Add("")
    [void]$lines.Add("**All records below are fictional demo data. Do not use real customer, employee, vendor or tender information in this environment.**")
    [void]$lines.Add("")
    [void]$lines.Add("- Run id: ``$($Manifest.run_id)``")
    [void]$lines.Add("- Prepared at: $($Manifest.created_at)")
    [void]$lines.Add("- Scenario: ``$($Manifest.scenario)``")
    [void]$lines.Add("- Application: http://localhost:3000")
    [void]$lines.Add("- Login page: http://localhost:3000/login")
    [void]$lines.Add("")
    [void]$lines.Add("Reset command: ``.\scripts\vendor-demo.ps1 reset``")
    [void]$lines.Add("Cleanup command: ``.\scripts\vendor-demo.ps1 cleanup``")
    [void]$lines.Add("")
    [void]$lines.Add("See ``docs/demo/PBL_CRM_VENDOR_DEMO_RUNBOOK.md`` for the full walkthrough script,")
    [void]$lines.Add("``docs/demo/PBL_CRM_VENDOR_DEMO_SCENARIO_MATRIX.md`` for scenario-by-scenario detail, and")
    [void]$lines.Add("``docs/demo/PBL_CRM_VENDOR_DEMO_PRESENTER_CHECKLIST.md`` for pre-demo preparation steps.")
    [void]$lines.Add("")
    [void]$lines.Add("## Records")
    [void]$lines.Add("")
    [void]$lines.Add("| Track | Record | Interactive? | Presenter role | Presenter action | Expected result | Link |")
    [void]$lines.Add("| --- | --- | --- | --- | --- | --- | --- |")

    $recordNames = $Manifest.records.PSObject.Properties.Name | Sort-Object
    foreach ($key in $recordNames) {
        $record = $Manifest.records.$key
        $meta = $record.demo_meta
        if (-not $meta) { continue }

        $link = ""
        foreach ($suffix in @("amendment", "lead", "commercial_offer", "account")) {
            $candidateKey = "$key.$suffix"
            if ($Manifest.urls.PSObject.Properties.Name -contains $candidateKey) {
                $link = $Manifest.urls.$candidateKey
                break
            }
        }
        $interactiveLabel = if ($meta.interactive) { "**Yes**" } else { "No (fallback)" }
        [void]$lines.Add("| $($meta.track) | ``$key`` | $interactiveLabel | $($meta.presenter_role) | $($meta.presenter_action) | $($meta.expected_result) | $link |")
    }

    [void]$lines.Add("")
    [void]$lines.Add("## Fallback map")
    [void]$lines.Add("")
    [void]$lines.Add("If an interactive step was already performed, was skipped, or the session was lost, use its paired fallback record instead of repeating the live action:")
    [void]$lines.Add("")
    foreach ($key in $recordNames) {
        $record = $Manifest.records.$key
        $meta = $record.demo_meta
        if ($meta -and $meta.fallback_of) {
            [void]$lines.Add("- ``$key`` is the fallback for ``$($meta.fallback_of)``.")
        }
    }

    [void]$lines.Add("")
    [void]$lines.Add("## All record URLs")
    [void]$lines.Add("")
    foreach ($urlKey in ($Manifest.urls.PSObject.Properties.Name | Sort-Object)) {
        [void]$lines.Add("- ``$urlKey``: $($Manifest.urls.$urlKey)")
    }

    New-Item -ItemType Directory -Force -Path $demoDir | Out-Null
    Set-Content -Path $launchSheetPath -Value ($lines -join "`r`n") -Encoding utf8
}

function Invoke-Prepare {
    if (Test-Path $activeRunPath) {
        $existing = Get-ActiveManifest
        $existingRunId = if ($existing) { $existing.run_id } else { "(unreadable)" }
        Write-Error "An active vendor demo run already exists (run id $existingRunId). Run '.\scripts\vendor-demo.ps1 reset' to replace it, or '.\scripts\vendor-demo.ps1 cleanup' to remove it before preparing a new one."
        exit 1
    }

    Write-Host "Ensuring db/backend/frontend Compose services are up..."
    docker compose up -d db backend frontend
    if ($LASTEXITCODE -ne 0) { throw "docker compose up -d db backend frontend failed." }

    Write-Host "Waiting for backend health endpoint..."
    if (-not (Wait-ForHttp -Url "http://localhost:8000/api/health")) { throw "Backend did not become healthy in time." }
    Write-Host "Waiting for frontend..."
    if (-not (Wait-ForHttp -Url "http://localhost:3000/login")) { throw "Frontend did not become ready in time." }

    New-Item -ItemType Directory -Force -Path $demoDir | Out-Null

    Write-Host "Seeding $scenario..."
    $seedOutput = docker compose exec -T backend python -m tooling.smoke_data seed --scenario $scenario --json
    if ($LASTEXITCODE -ne 0) {
        Write-Host $seedOutput
        throw "Seeding $scenario failed; see output above. No active demo run was created."
    }

    $manifestJson = ($seedOutput -join "`n")
    Set-Content -Path $activeRunPath -Value $manifestJson -Encoding utf8
    $manifest = $manifestJson | ConvertFrom-Json

    New-LaunchSheet -Manifest $manifest

    Write-Host ""
    Write-Host "Vendor demo prepared."
    Write-Host "Run id:        $($manifest.run_id)"
    Write-Host "Launch sheet:  $launchSheetPath"
    Write-Host "Application:   http://localhost:3000"
    Write-Host "Login page:    http://localhost:3000/login"
}

function Invoke-Status {
    if (-not (Test-Path $activeRunPath)) {
        Write-Host "No active vendor demo run. Run '.\scripts\vendor-demo.ps1 prepare' to create one."
        exit 0
    }
    $manifest = Get-ActiveManifest
    if (-not $manifest) {
        Write-Warning "The active run file is unreadable. Run '.\scripts\vendor-demo.ps1 cleanup' to clear it, then 'prepare' again."
        exit 1
    }

    Write-Host "Active run id: $($manifest.run_id)"
    Write-Host "Scenario:      $($manifest.scenario)"
    Write-Host "Prepared at:   $($manifest.created_at)"
    Write-Host "Launch sheet:  $launchSheetPath"
    Write-Host ""

    $statusExit = Invoke-BackendStatus -RunId $manifest.run_id -RequirePresent
    if ($statusExit -ne 0) {
        Write-Warning "Some anchor records are missing. Recommend running '.\scripts\vendor-demo.ps1 reset' before demonstrating."
    }
    exit $statusExit
}

function Invoke-Preflight {
    if (-not (Test-Path $activeRunPath)) {
        Write-Error "No active vendor demo run. Run '.\scripts\vendor-demo.ps1 prepare' first."
        exit 1
    }
    $manifest = Get-ActiveManifest
    if (-not $manifest) {
        Write-Error "The active run file is unreadable. Run '.\scripts\vendor-demo.ps1 cleanup' then 'prepare' again."
        exit 1
    }

    Write-Host "Checking backend health endpoint..."
    if (-not (Wait-ForHttp -Url "http://localhost:8000/api/health" -TimeoutSeconds 15)) { throw "Backend is not healthy." }
    Write-Host "Checking frontend login page..."
    if (-not (Wait-ForHttp -Url "http://localhost:3000/login" -TimeoutSeconds 15)) { throw "Frontend is not reachable." }

    Write-Host "Checking active run's anchor records..."
    $statusExit = Invoke-BackendStatus -RunId $manifest.run_id -RequirePresent
    if ($statusExit -ne 0) {
        Write-Warning "Anchor records are missing; recommend '.\scripts\vendor-demo.ps1 reset' before the live demo."
    }

    New-Item -ItemType Directory -Force -Path $e2eManifestDir | Out-Null
    Copy-Item -Path $activeRunPath -Destination $e2eManifestPath -Force

    Write-Host "Running the non-destructive Playwright demo-preflight suite (docker compose --profile e2e run --rm e2e)..."
    # All four manifest env vars point at the same vendor-demo-bundle manifest. Every other
    # (non-demo-preflight) spec file still executes its own top-level loadXManifest() call
    # during Playwright's test collection, but each already has its own test.skip(!record, ...)
    # guard for a manifest that is missing its expected record keys -- which is exactly what
    # this manifest is missing for their scenarios, so they skip cleanly instead of failing.
    # e2e/tests/global-setup.ts independently gates each of its own loadXManifest() calls on
    # the matching env var, so it no longer depends on this exact four-env-var combination
    # either -- but keep setting all four here anyway, since it is what lets the *other* spec
    # files' own test.skip(...) guards (not global-setup.ts) resolve cleanly during collection.
    docker compose --profile e2e run --rm `
        -e MANIFEST_PATH="/e2e/.manifest/vendor-demo.json" `
        -e RELATED_OFFERS_MANIFEST_PATH="/e2e/.manifest/vendor-demo.json" `
        -e WORK_ORDER_AMENDMENTS_MANIFEST_PATH="/e2e/.manifest/vendor-demo.json" `
        -e VENDOR_DEMO_MANIFEST_PATH="/e2e/.manifest/vendor-demo.json" `
        e2e bash -c "npm install --no-audit --no-fund && npx playwright test --grep '@demo-preflight'"
    $playwrightExit = $LASTEXITCODE

    if ($statusExit -ne 0 -or $playwrightExit -ne 0) {
        Write-Warning "Preflight FAILED (status exit $statusExit, Playwright exit $playwrightExit)."
        exit 1
    }
    Write-Host "Preflight PASSED."
    exit 0
}

function Invoke-Reset {
    if (Test-Path $activeRunPath) {
        $existing = Get-ActiveManifest
        if ($existing) {
            Write-Host "Cleaning up the current active run $($existing.run_id) before preparing a fresh one..."
            $cleanupExit = Invoke-BackendCleanup -RunId $existing.run_id
            if ($cleanupExit -ne 0) {
                Write-Warning "Cleanup of the previous active run failed (exit $cleanupExit). Inspect manually with '.\scripts\smoke-data.ps1 cleanup -RunId $($existing.run_id)' before retrying reset."
                exit 1
            }
        } else {
            Write-Warning "The previous active run file was unreadable and could not be cleaned up by run id. Check '.\scripts\smoke-data.ps1 list' for orphaned runs if needed."
        }
        Remove-Item -Path $activeRunPath -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $launchSheetPath -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "No active vendor demo run found; preparing a fresh one."
    }

    Invoke-Prepare
}

function Invoke-Cleanup {
    if (-not (Test-Path $activeRunPath)) {
        Write-Host "No active vendor demo run found. Nothing to clean up."
        exit 0
    }
    $manifest = Get-ActiveManifest
    if (-not $manifest) {
        Write-Warning "The active run file is unreadable and cannot be safely cleaned up by run id. Check '.\scripts\smoke-data.ps1 list' for orphaned runs, clean them up with '.\scripts\smoke-data.ps1 cleanup -RunId <id>', then remove $activeRunPath manually."
        exit 1
    }

    Write-Host "Cleaning up active run $($manifest.run_id)..."
    $cleanupExit = Invoke-BackendCleanup -RunId $manifest.run_id
    if ($cleanupExit -ne 0) {
        Write-Warning "Cleanup failed (exit $cleanupExit). Active run files were left in place so you can retry '.\scripts\vendor-demo.ps1 cleanup'."
        exit 1
    }

    Remove-Item -Path $activeRunPath -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $launchSheetPath -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $e2eManifestPath -Force -ErrorAction SilentlyContinue
    Write-Host "Vendor demo run cleaned up."
    exit 0
}

switch ($Command) {
    "prepare" { Invoke-Prepare; exit 0 }
    "status" { Invoke-Status }
    "preflight" { Invoke-Preflight }
    "reset" { Invoke-Reset; exit 0 }
    "cleanup" { Invoke-Cleanup }
}
