<#
.SYNOPSIS
    TE-1 end-to-end orchestration: builds the current frontend image, ensures
    db/backend/frontend are up, seeds the core-regression-bundle scenario through
    the backend smoke-data harness, runs the isolated Playwright suite against it,
    and always attempts cleanup afterwards -- even if the tests fail.

    Cleanup covers both the seeded business records (via the three run manifests) and
    the login audit events the specs create by authenticating through the real /login
    form. The latter are removed only above a boundary captured before the run and only
    for the explicitly listed E2E actor usernames, so pre-existing and unrelated events
    are preserved.

    Capturing that boundary is a hard prerequisite, not a best-effort step: it runs
    before seeding, and the script aborts if it fails or does not return a non-negative
    integer. Without a valid boundary the run would create login events it could not
    safely clean up, so Playwright must not start.

    Login events above the boundary belonging to an actor outside the allowlist are
    never deleted. They are reported and turn the run's exit code non-zero, so a future
    spec that logs in as a new seed user fails loudly rather than leaking audit rows.

.DESCRIPTION
    The frontend image is built before the services start. Since TE-2A the
    frontend Compose service has no source bind mount: it serves the production
    bundle baked into its image. `docker compose up -d` reuses an existing image
    without rebuilding it, so without this build step the suite could seed current
    data, exercise a stale frontend bundle, and still report success.

    Exit code is the Playwright test exit code when tests run and fail. If the
    tests pass but cleanup afterwards fails -- including the login-event cleanup --
    the cleanup failure is reported separately and becomes the exit code (so it is
    not silently swallowed), but it never masks a genuine test failure.

.PARAMETER SkipServiceStart
    Skips both the frontend image build and the Compose service start. The caller
    then owns supplying the intended running services and frontend image, and is
    responsible for the fact that the suite may not be testing current source.

.EXAMPLE
    .\scripts\run-e2e.ps1
#>

param(
    [switch]$SkipServiceStart
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
# Built one segment at a time rather than as a single "e2e\.manifest" literal: PowerShell 7
# runs on the Ubuntu CI runner, where a backslash is an ordinary filename character and the
# combined literal would create a file called "e2e\.manifest" instead of a directory. Join-Path
# emits the correct separator for the host, so the same script serves Windows and Linux.
$manifestDir = Join-Path (Join-Path $repoRoot "e2e") ".manifest"
$manifestPath = Join-Path $manifestDir "run.json"
$relatedOffersManifestPath = Join-Path $manifestDir "related-offers.json"
$workOrderAmendmentsManifestPath = Join-Path $manifestDir "work-order-amendments.json"

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

if (-not $SkipServiceStart) {
    # The frontend service has no source bind mount (TE-2A): it serves the bundle built into its
    # image. Build first so the suite tests current frontend source rather than a stale image.
    Write-Host "Building the current frontend image..."
    docker compose build frontend
    if ($LASTEXITCODE -ne 0) { throw "docker compose build frontend failed." }

    Write-Host "Ensuring db/backend/frontend Compose services are up (recreating frontend on the freshly built image)..."
    docker compose up -d db backend frontend
    if ($LASTEXITCODE -ne 0) { throw "docker compose up -d db backend frontend failed." }
} else {
    Write-Host "-SkipServiceStart: skipping the frontend image build and Compose start."
    Write-Warning "The caller owns the running services and frontend image; this run may not be testing current frontend source."
}

Write-Host "Waiting for backend health endpoint..."
if (-not (Wait-ForHttp -Url "http://localhost:8000/api/health")) {
    throw "Backend did not become healthy in time."
}
Write-Host "Waiting for frontend..."
if (-not (Wait-ForHttp -Url "http://localhost:3000/login")) {
    throw "Frontend did not become ready in time."
}

New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null

# Captured BEFORE seeding, so a capture failure aborts while there is nothing to clean up.
# The suite logs in through the real /login form, so each spec writes genuine
# UserLoginSucceeded audit rows that the manifest cleanup cannot know about (they belong to
# app_user, not to a seeded record). Without a valid boundary those rows cannot be removed
# safely, so this is a hard prerequisite rather than a best-effort step: the run must not
# create login events it has no way to clean up.
Write-Host "Capturing business_event boundary before seeding..."
$eventBoundaryOutput = docker compose exec -T backend python -m tooling.smoke_data event-boundary
if ($LASTEXITCODE -ne 0) {
    Write-Host $eventBoundaryOutput
    throw "Could not capture the business_event boundary. Aborting before seeding; nothing was created, so there is nothing to clean up."
}

$eventBoundary = ($eventBoundaryOutput | Select-Object -Last 1).ToString().Trim()
if ($eventBoundary -notmatch '^\d+$') {
    throw "business_event boundary '$eventBoundary' is not a non-negative integer. Aborting before seeding."
}
Write-Host "business_event boundary: $eventBoundary"

# The E2E actor allowlist is passed explicitly rather than relying on the CLI default, so
# the deletion scope is visible at the call site. Any login event above the boundary by an
# actor outside this list is reported and fails the run instead of being deleted. finance1 and
# ops1 were added on 11 September 2026 for the document-upload spec, which logs in as each to
# check the upload form on the record type their role may not change (they are the two roles at
# which the Account and Commercial Offer upload-role sets diverge).
$e2eActors = "admin1,sales1,readonly1,finance1,ops1"

Write-Host "Seeding core-regression-bundle..."
$seedOutput = docker compose exec -T backend python -m tooling.smoke_data seed --scenario core-regression-bundle --json
if ($LASTEXITCODE -ne 0) {
    Write-Host $seedOutput
    throw "Seeding core-regression-bundle failed; see output above. No E2E run started, nothing to clean up."
}

$manifestJson = ($seedOutput -join "`n")
Set-Content -Path $manifestPath -Value $manifestJson -Encoding utf8
$manifest = $manifestJson | ConvertFrom-Json
$runId = $manifest.run_id
Write-Host "Seeded run id: $runId"
Write-Host "Manifest written to: $manifestPath"

Write-Host "Seeding related-offer-regression-bundle (Slice 6O.1)..."
$relatedOffersSeedOutput = docker compose exec -T backend python -m tooling.smoke_data seed --scenario related-offer-regression-bundle --json
if ($LASTEXITCODE -ne 0) {
    Write-Host $relatedOffersSeedOutput
    Write-Host "Cleaning up run $runId before aborting..."
    docker compose exec -T backend python -m tooling.smoke_data cleanup --run-id $runId
    throw "Seeding related-offer-regression-bundle failed; see output above."
}

$relatedOffersManifestJson = ($relatedOffersSeedOutput -join "`n")
Set-Content -Path $relatedOffersManifestPath -Value $relatedOffersManifestJson -Encoding utf8
$relatedOffersManifest = $relatedOffersManifestJson | ConvertFrom-Json
$relatedOffersRunId = $relatedOffersManifest.run_id
Write-Host "Seeded related-offer run id: $relatedOffersRunId"
Write-Host "Related-offer manifest written to: $relatedOffersManifestPath"

Write-Host "Seeding work-order-amendment-regression-bundle (Slice 6O.2)..."
$workOrderAmendmentsSeedOutput = docker compose exec -T backend python -m tooling.smoke_data seed --scenario work-order-amendment-regression-bundle --json
if ($LASTEXITCODE -ne 0) {
    Write-Host $workOrderAmendmentsSeedOutput
    Write-Host "Cleaning up runs $runId and $relatedOffersRunId before aborting..."
    docker compose exec -T backend python -m tooling.smoke_data cleanup --run-id $runId
    docker compose exec -T backend python -m tooling.smoke_data cleanup --run-id $relatedOffersRunId
    throw "Seeding work-order-amendment-regression-bundle failed; see output above."
}

$workOrderAmendmentsManifestJson = ($workOrderAmendmentsSeedOutput -join "`n")
Set-Content -Path $workOrderAmendmentsManifestPath -Value $workOrderAmendmentsManifestJson -Encoding utf8
$workOrderAmendmentsManifest = $workOrderAmendmentsManifestJson | ConvertFrom-Json
$workOrderAmendmentsRunId = $workOrderAmendmentsManifest.run_id
Write-Host "Seeded work-order-amendment run id: $workOrderAmendmentsRunId"
Write-Host "Work Order Amendments manifest written to: $workOrderAmendmentsManifestPath"

$testExitCode = 0
try {
    Write-Host "Running Playwright suite (docker compose --profile e2e run --rm e2e)..."
    docker compose --profile e2e run --rm e2e
    $testExitCode = $LASTEXITCODE
} finally {
    Write-Host "Cleaning up seeded run $runId..."
    docker compose exec -T backend python -m tooling.smoke_data cleanup --run-id $runId
    $cleanupExitCode = $LASTEXITCODE
    if ($cleanupExitCode -ne 0) {
        Write-Warning "Cleanup for run $runId FAILED (exit code $cleanupExitCode). Seeded test data may remain. IF the failure names stored files that could not be deleted, those keys appear ONLY in the output above -- re-running cleanup cannot find them again, because their database rows are already gone. Capture that output before closing this window. For any other failure, retry with '.\scripts\smoke-data.ps1 cleanup -RunId $runId'."
    } else {
        Write-Host "Cleanup for run $runId completed."
    }

    Write-Host "Cleaning up seeded run $relatedOffersRunId..."
    docker compose exec -T backend python -m tooling.smoke_data cleanup --run-id $relatedOffersRunId
    $relatedOffersCleanupExitCode = $LASTEXITCODE
    if ($relatedOffersCleanupExitCode -ne 0) {
        Write-Warning "Cleanup for run $relatedOffersRunId FAILED (exit code $relatedOffersCleanupExitCode). Seeded test data may remain. IF the failure names stored files that could not be deleted, those keys appear ONLY in the output above -- re-running cleanup cannot find them again, because their database rows are already gone. Capture that output before closing this window. For any other failure, retry with '.\scripts\smoke-data.ps1 cleanup -RunId $relatedOffersRunId'."
        $cleanupExitCode = $relatedOffersCleanupExitCode
    } else {
        Write-Host "Cleanup for run $relatedOffersRunId completed."
    }

    Write-Host "Cleaning up seeded run $workOrderAmendmentsRunId..."
    docker compose exec -T backend python -m tooling.smoke_data cleanup --run-id $workOrderAmendmentsRunId
    $workOrderAmendmentsCleanupExitCode = $LASTEXITCODE
    if ($workOrderAmendmentsCleanupExitCode -ne 0) {
        Write-Warning "Cleanup for run $workOrderAmendmentsRunId FAILED (exit code $workOrderAmendmentsCleanupExitCode). Seeded test data may remain. IF the failure names stored files that could not be deleted, those keys appear ONLY in the output above -- re-running cleanup cannot find them again, because their database rows are already gone. Capture that output before closing this window. For any other failure, retry with '.\scripts\smoke-data.ps1 cleanup -RunId $workOrderAmendmentsRunId'."
        $cleanupExitCode = $workOrderAmendmentsCleanupExitCode
    } else {
        Write-Host "Cleanup for run $workOrderAmendmentsRunId completed."
    }

    # Login audit events written by the Playwright specs' real form logins. Restricted to
    # ids above the pre-run boundary and to the explicitly listed E2E actor usernames, so
    # pre-existing events and every non-login event are preserved. Exit code 3 means login
    # events by an actor outside the allowlist survived: they are deliberately left in place
    # and reported, so a future spec using a new seed user fails loudly here.
    Write-Host "Cleaning up E2E login audit events above business_event id $eventBoundary (actors: $e2eActors)..."
    docker compose exec -T backend python -m tooling.smoke_data cleanup-login-events --after-id $eventBoundary --actors $e2eActors
    $loginEventCleanupExitCode = $LASTEXITCODE
    if ($loginEventCleanupExitCode -ne 0) {
        Write-Warning "E2E login-event cleanup FAILED (exit code $loginEventCleanupExitCode). See the output above; login audit rows created by this run may remain."
        $cleanupExitCode = $loginEventCleanupExitCode
    }
}

if ($testExitCode -ne 0) {
    Write-Warning "Playwright suite failed (exit code $testExitCode). Failure artifacts, if any, are under e2e\playwright-report and e2e\test-results."
    exit $testExitCode
}

if ($cleanupExitCode -ne 0) {
    Write-Warning "Playwright suite passed, but cleanup failed. Reporting the cleanup failure as this run's exit code."
    exit $cleanupExitCode
}

Write-Host "E2E run complete: tests passed and cleanup succeeded."
exit 0
