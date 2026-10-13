<#
.SYNOPSIS
    TE-2C migrated-foundation standard-interaction timing baseline.

.DESCRIPTION
    Measures round-trip latency for a small set of representative, already-existing standard
    interactions against the local Compose stack, and reports min/median/p95/max over a
    repeatable warm-up-then-measure method.

    This is a MIGRATED-FOUNDATION BASELINE, NOT a load test and NOT a production performance
    certification. It exercises exactly one client against a local development machine; it
    represents no agreed normal-load profile, no production-like concurrency, and no
    production-like data volume. Whether observed samples fall above or below the ERP source's
    "95% of standard interactions within 2 seconds" figure is reported for local context only
    -- this script and its output must never be cited as evidence that NFR is met. See
    docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md.

    Interactions measured:
      1. GET /api/health              -- unauthenticated liveness endpoint. Stable, read-only,
                                          creates no persisted state.
      2. GET /api/accounts?limit=20   -- a representative authenticated business read. Read-only;
                                          creates no persisted state per request.

    LOCAL-DEVELOPMENT-ONLY BOUNDARY. -BaseUrl is restricted to a loopback target
    (http://localhost[:port] or http://127.0.0.1[:port]) and the script refuses to run against
    anything else -- see Test-LoopbackUrl below. This is local-development tooling only; it must
    never be pointed at a remote or production URL merely because the parameter happens to be
    configurable.

    AUTHENTICATION WITHOUT AN AUDIT-EVENT SIDE EFFECT, NARROWLY SCOPED. A real login through
    /api/auth/login always writes a UserLoginSucceeded business_event, by design -- correct for a
    real login, but not something this script should create every time it measures a timing
    baseline (and broadly deleting "every readonly1 login event above a boundary" afterward would
    risk removing a concurrent, genuine login by someone else). Instead this script obtains its
    bearer token via `python -m tooling.smoke_data issue-test-token`
    (backend/tooling/smoke_data/auth_tokens.py), which reuses the exact identity-lookup and
    token-signing code the real login route uses but never calls that route and never writes a
    business_event. That tool is deliberately narrow: it takes no username parameter and will
    only ever issue a token for the fixed, already-documented readonly1 seed identity; it refuses
    to run unless APP_ENV is EXPLICITLY PRESENT in the process environment and equal to a
    permitted local development/test value (an entirely unset APP_ENV is refused, never silently
    treated as development); and the issued token is short-lived (5 minutes), not the
    application's normal long-lived session duration. This is a materially different and more
    scoped trust boundary than backend/tooling/smoke_data/actors.py, which only resolves a
    username for direct in-process service calls and never produces anything replayable as an
    HTTP credential -- the two are not equivalent. Running this script repeatedly creates zero
    persistent audit/business state -- there is nothing to clean up.

    PRINTING CONTRACT, stated precisely. `issue-test-token` intentionally writes exactly the
    bearer token to stdout -- that is its whole purpose as a command this script can capture.
    This script captures that stdout and never displays or echoes it, on the success path or on
    any failure path (the failure path prints only a fixed, generic message and never the
    captured command output, so a future refactor cannot accidentally start echoing a real
    token). The underlying helper itself writes no token to stderr or to any surrounding
    human-readable diagnostic text.

    NO REDIRECT FOLLOWING. Every request (health probe, warm-up and measured) is made with
    `-MaximumRedirection 0`, so an unexpected 3xx response fails the request rather than being
    silently followed to wherever it points -- the loopback-only guarantee above applies to the
    actual request made, not merely to the -BaseUrl string it started from.

    Percentiles use the nearest-rank method: for P iterations and target percentile p, the
    reported value is the element at 1-indexed position ceil(p/100 * P), clamped to [1, P], of
    the ascending-sorted sample array. This is a simple, defensible, commonly used method; no
    interpolation library is introduced.

.PARAMETER WarmupCount
    Number of untimed warm-up requests per interaction before measurement begins. Default 3.
    Must be >= 0; enforced by parameter validation, so an invalid value fails immediately rather
    than silently producing a trivial or meaningless result.

.PARAMETER SampleCount
    Number of timed, measured requests per interaction. Default 20. Must be >= 1; enforced by
    parameter validation. SampleCount=0 would otherwise report "0/0 succeeded" as a false PASS,
    since zero requested equals zero succeeded -- this is rejected before any request is made.

.PARAMETER BaseUrl
    Backend base URL. Must be a loopback URL (http://localhost[:port] or
    http://127.0.0.1[:port]); any other host is rejected before any request is made. Defaults to
    the documented local Compose mapping.

.EXAMPLE
    .\scripts\te-2c-timing-baseline.ps1

.EXAMPLE
    .\scripts\te-2c-timing-baseline.ps1 -SampleCount 50 -WarmupCount 5

.EXAMPLE
    .\scripts\te-2c-timing-baseline.ps1 -SampleCount 0
    # Fails immediately with a parameter validation error -- this is the expected, documented
    # negative-boundary behaviour, not a bug.
#>

param(
    [ValidateRange(0, [int]::MaxValue)]
    [int]$WarmupCount = 3,

    [ValidateRange(1, [int]::MaxValue)]
    [int]$SampleCount = 20,

    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------------------
# Pure helpers: percentile calculation and the local-development URL boundary guard. Kept
# small and dependency-free so they are easy to read and reason about.
# ---------------------------------------------------------------------------------------

function Test-LoopbackUrl {
    <#
        Local-development-only boundary (finding 5). Accepts only http://localhost[:port] or
        http://127.0.0.1[:port], with an optional path. Deliberately does not accept https --
        this repository's local Compose stack serves plain HTTP -- and does not accept any other
        hostname, so a configurable -BaseUrl can never send this script's requests to a remote
        or production target.
    #>
    param([string]$Url)
    return $Url -match '^http://(localhost|127\.0\.0\.1)(:\d+)?(/.*)?$'
}

function Get-NearestRankPercentile {
    param([double[]]$SortedAscendingValues, [double]$Percentile)
    $n = $SortedAscendingValues.Count
    if ($n -eq 0) { throw "Cannot compute a percentile of an empty sample set." }
    $rank = [Math]::Ceiling(($Percentile / 100.0) * $n)
    if ($rank -lt 1) { $rank = 1 }
    if ($rank -gt $n) { $rank = $n }
    return $SortedAscendingValues[$rank - 1]
}

function Get-Median {
    param([double[]]$SortedAscendingValues)
    $n = $SortedAscendingValues.Count
    if ($n -eq 0) { throw "Cannot compute the median of an empty sample set." }
    if ($n % 2 -eq 1) {
        return $SortedAscendingValues[[Math]::Floor($n / 2)]
    }
    $lower = $SortedAscendingValues[($n / 2) - 1]
    $upper = $SortedAscendingValues[$n / 2]
    return ($lower + $upper) / 2.0
}

function Measure-Interaction {
    <#
        Runs $WarmupCount untimed requests followed by $SampleCount timed requests against a
        request scriptblock (which must return an object with .StatusCode). Returns a result
        object with raw samples and success/failure counts. Never throws on an individual
        request failure -- failures are counted and surfaced in the result for the caller to
        act on, so one flaky request does not abort the whole baseline run uninformatively.
    #>
    param(
        [string]$Name,
        [scriptblock]$RequestFn,
        [int]$WarmupCount,
        [int]$SampleCount
    )

    if ($WarmupCount -gt 0) {
        Write-Host "Warming up '$Name' ($WarmupCount request(s), untimed)..."
        for ($i = 1; $i -le $WarmupCount; $i++) {
            try { & $RequestFn | Out-Null } catch { Write-Warning "Warm-up request $i for '$Name' failed: $($_.Exception.Message)" }
        }
    }

    Write-Host "Measuring '$Name' ($SampleCount request(s), timed)..."
    $samples = New-Object System.Collections.Generic.List[double]
    $failures = New-Object System.Collections.Generic.List[string]
    $stopwatch = [System.Diagnostics.Stopwatch]::new()

    for ($i = 1; $i -le $SampleCount; $i++) {
        $stopwatch.Restart()
        try {
            $response = & $RequestFn
            $stopwatch.Stop()
            if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
                $failures.Add("iteration ${i}: unexpected status $($response.StatusCode)")
            } else {
                $samples.Add([double]$stopwatch.Elapsed.TotalMilliseconds)
            }
        } catch {
            $stopwatch.Stop()
            $failures.Add("iteration ${i}: $($_.Exception.Message)")
        }
    }

    return [pscustomobject]@{
        Name         = $Name
        RequestedN   = $SampleCount
        SuccessCount = $samples.Count
        FailureCount = $failures.Count
        Failures     = $failures
        SamplesMs    = @($samples | Sort-Object)
    }
}

function Format-InteractionResult {
    param($Result)
    if ($Result.SuccessCount -eq 0) {
        Write-Host ("{0}: 0/{1} succeeded -- no timing data." -f $Result.Name, $Result.RequestedN)
        return [pscustomobject]@{
            Name = $Result.Name; SuccessCount = 0; RequestedN = $Result.RequestedN
            FailureCount = $Result.FailureCount; MinMs = $null; MedianMs = $null; P95Ms = $null; MaxMs = $null
            RawSamplesMs = @()
        }
    }
    $sorted = $Result.SamplesMs
    $min = $sorted[0]
    $max = $sorted[$sorted.Count - 1]
    $median = Get-Median -SortedAscendingValues $sorted
    $p95 = Get-NearestRankPercentile -SortedAscendingValues $sorted -Percentile 95
    Write-Host ("{0}: n={1}/{2} success, min={3:N1}ms median={4:N1}ms p95={5:N1}ms max={6:N1}ms" -f `
        $Result.Name, $Result.SuccessCount, $Result.RequestedN, $min, $median, $p95, $max)
    if ($p95 -gt 2000) {
        Write-Host ("  (local context only: p95 exceeds 2000ms; this is NOT an NFR-compliance statement -- no agreed normal-load profile is represented here)")
    } else {
        Write-Host ("  (local context only: p95 is at or under 2000ms on this single-client local sample -- NOT an NFR-compliance statement)")
    }
    return [pscustomobject]@{
        Name          = $Result.Name
        SuccessCount  = $Result.SuccessCount
        RequestedN    = $Result.RequestedN
        FailureCount  = $Result.FailureCount
        MinMs         = [math]::Round($min, 2)
        MedianMs      = [math]::Round($median, 2)
        P95Ms         = [math]::Round($p95, 2)
        MaxMs         = [math]::Round($max, 2)
        RawSamplesMs  = @($sorted | ForEach-Object { [math]::Round($_, 2) })
    }
}

# ---------------------------------------------------------------------------------------
# Setup: local-development URL boundary, reachability, and a test bearer token that never
# creates a login audit event.
# ---------------------------------------------------------------------------------------

$overallExitCode = 0

try {
    Write-Host "=== TE-2C standard-interaction timing baseline ==="
    Write-Host "Base URL: $BaseUrl"
    Write-Host "Warm-up count: $WarmupCount, sample count: $SampleCount"
    Write-Host "Environment: local Docker Compose (single client, no concurrency, no agreed load profile)."
    Write-Host ""

    if (-not (Test-LoopbackUrl -Url $BaseUrl)) {
        throw "Refusing to run: -BaseUrl '$BaseUrl' is not a loopback URL (http://localhost[:port] or http://127.0.0.1[:port]). This is local-development-only tooling and must never target a remote or production URL."
    }

    Write-Host "Confirming backend health endpoint is reachable..."
    $healthProbe = Invoke-WebRequest -Uri "$BaseUrl/api/health" -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 0
    if ($healthProbe.StatusCode -ne 200) {
        throw "Backend health check returned unexpected status $($healthProbe.StatusCode); aborting."
    }
    Write-Host "Backend reachable."

    Write-Host "Issuing a short-lived test bearer token for the fixed readonly1 identity (no login audit event is created; this script never displays or echoes the token, on success or failure)..."
    # Deliberately never Write-Host the raw command output on ANY path, including failure: the
    # success line legitimately IS the token, so a failure branch that echoed the same captured
    # variable would risk one day echoing a real token if this code were ever refactored. On
    # failure, only a fixed, generic message is shown; run the command manually for diagnostics.
    $tokenCommandOutput = docker compose exec -T backend python -m tooling.smoke_data issue-test-token 2>$null
    $tokenCommandExit = $LASTEXITCODE
    if ($tokenCommandExit -ne 0) {
        throw "Could not issue a test bearer token (exit $tokenCommandExit). Run 'docker compose exec -T backend python -m tooling.smoke_data issue-test-token' directly to see the underlying error; its output is not reproduced here so a token can never be echoed by this failure path."
    }
    $token = ($tokenCommandOutput | Select-Object -Last 1).ToString().Trim()
    if (-not $token) {
        throw "Token issuance reported success but returned no token; cannot measure the authenticated interaction."
    }
    Write-Host "Token acquired (not displayed); no business_event was created to obtain it."

    $authHeaders = @{ Authorization = "Bearer $token" }

    # ---------------------------------------------------------------------------------------
    # Measure
    # ---------------------------------------------------------------------------------------

    # -MaximumRedirection 0 on every request (health probe above, and both scriptblocks here): an
    # unexpected 3xx throws rather than being followed, so the loopback-only guarantee applies to
    # what is actually requested, not merely to the -BaseUrl string these requests started from.
    $healthResult = Measure-Interaction -Name "GET /api/health (unauthenticated)" `
        -RequestFn { Invoke-WebRequest -Uri "$BaseUrl/api/health" -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 0 } `
        -WarmupCount $WarmupCount -SampleCount $SampleCount

    $accountsResult = Measure-Interaction -Name "GET /api/accounts?limit=20 (authenticated read)" `
        -RequestFn { Invoke-WebRequest -Uri "$BaseUrl/api/accounts?limit=20" -Headers $authHeaders -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 0 } `
        -WarmupCount $WarmupCount -SampleCount $SampleCount

    Write-Host ""
    Write-Host "--- Results ---"
    $summaryHealth = Format-InteractionResult -Result $healthResult
    $summaryAccounts = Format-InteractionResult -Result $accountsResult

    Write-Host ""
    Write-Host "--- Raw samples (ms, ascending) ---"
    $healthRawJoined = ($healthResult.SamplesMs | ForEach-Object { [math]::Round($_, 1) }) -join ", "
    $accountsRawJoined = ($accountsResult.SamplesMs | ForEach-Object { [math]::Round($_, 1) }) -join ", "
    Write-Host ("{0}: [{1}]" -f $healthResult.Name, $healthRawJoined)
    Write-Host ("{0}: [{1}]" -f $accountsResult.Name, $accountsRawJoined)

    $anyFailures = ($healthResult.FailureCount -gt 0) -or ($accountsResult.FailureCount -gt 0)
    $anyIncomplete = ($healthResult.SuccessCount -ne $SampleCount) -or ($accountsResult.SuccessCount -ne $SampleCount)

    if ($healthResult.FailureCount -gt 0) {
        Write-Host ""
        Write-Warning "Failures for '$($healthResult.Name)':"
        $healthResult.Failures | ForEach-Object { Write-Warning "  $_" }
    }
    if ($accountsResult.FailureCount -gt 0) {
        Write-Host ""
        Write-Warning "Failures for '$($accountsResult.Name)':"
        $accountsResult.Failures | ForEach-Object { Write-Warning "  $_" }
    }

    Write-Host ""
    Write-Host "--- Machine-readable summary ---"
    ([pscustomobject]@{
        base_url      = $BaseUrl
        warmup_count  = $WarmupCount
        sample_count  = $SampleCount
        interactions  = @($summaryHealth, $summaryAccounts)
    } | ConvertTo-Json -Depth 5)

    if ($anyFailures -or $anyIncomplete) {
        throw "Timing baseline INCOMPLETE or contains failures: not all $SampleCount requested samples succeeded for every interaction. See failures above."
    }

    Write-Host ""
    Write-Host "TE-2C timing baseline: PASS (repeatable baseline recorded; this is NOT an NFR/production performance certification)."
    $overallExitCode = 0
} catch {
    Write-Host ""
    Write-Error "TE-2C timing baseline: FAIL`n$($_.Exception.Message)"
    $overallExitCode = 1
}

exit $overallExitCode
