<#
.SYNOPSIS
    Thin PowerShell wrapper around the TE-1 backend smoke-data harness
    (backend/tooling/smoke_data). Always runs Python inside the backend
    Docker Compose service -- never expects a host Python install.

.DESCRIPTION
    -Manifest and -ManifestOut are paths resolved INSIDE the backend container
    (`docker compose exec` runs there, not on the host), so a host-relative
    path such as .\e2e\.manifest\run.json will NOT resolve -- the backend
    container only has ./backend/app, ./backend/tests and ./backend/tooling
    mounted. Prefer -RunId for cleanup: it reads the manifest the backend
    already saved locally under its own backend/.smoke-runs/ at seed time, so
    no path needs to cross the host/container boundary at all. Only use
    -Manifest/-ManifestOut with a path that genuinely exists inside the
    backend container (e.g. under /tmp, which persists across separate
    `docker compose exec` calls against the same running container).

.EXAMPLE
    .\scripts\smoke-data.ps1 seed -Scenario core-regression-bundle

.EXAMPLE
    .\scripts\smoke-data.ps1 cleanup -RunId te1-1a2b3c4d

.EXAMPLE
    .\scripts\smoke-data.ps1 status -RunId te1-1a2b3c4d

.EXAMPLE
    .\scripts\smoke-data.ps1 list

.EXAMPLE
    .\scripts\smoke-data.ps1 scenarios
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("seed", "cleanup", "status", "list", "scenarios")]
    [string]$Command,

    [string]$Scenario,
    [string]$RunId,
    [string]$Manifest,
    [string]$ManifestOut,
    [switch]$Json
)

# Deliberately does NOT wrap the docker call in a helper function that does
# `return $LASTEXITCODE`: PowerShell functions capture every unsuppressed output
# object into the function's own return value, so the child process's stdout would
# be silently merged into (and corrupt) the "exit code" being returned. Each branch
# below calls docker directly and exits immediately from $LASTEXITCODE instead.

switch ($Command) {
    "seed" {
        if (-not $Scenario) {
            Write-Error "seed requires -Scenario <name>. Run '.\scripts\smoke-data.ps1 scenarios' to list options."
            exit 2
        }
        $cliArgs = @("seed", "--scenario", $Scenario)
        if ($Json) { $cliArgs += "--json" }
        if ($ManifestOut) { $cliArgs += @("--manifest-out", $ManifestOut) }
        docker compose exec -T backend python -m tooling.smoke_data @cliArgs
        exit $LASTEXITCODE
    }
    "cleanup" {
        if (-not $RunId -and -not $Manifest) {
            Write-Error "cleanup requires either -RunId <id> or -Manifest <path>."
            exit 2
        }
        $cliArgs = @("cleanup")
        if ($RunId) { $cliArgs += @("--run-id", $RunId) }
        if ($Manifest) { $cliArgs += @("--manifest", $Manifest) }
        docker compose exec -T backend python -m tooling.smoke_data @cliArgs
        exit $LASTEXITCODE
    }
    "status" {
        if (-not $RunId -and -not $Manifest) {
            Write-Error "status requires either -RunId <id> or -Manifest <path>."
            exit 2
        }
        $cliArgs = @("status")
        if ($RunId) { $cliArgs += @("--run-id", $RunId) }
        if ($Manifest) { $cliArgs += @("--manifest", $Manifest) }
        docker compose exec -T backend python -m tooling.smoke_data @cliArgs
        exit $LASTEXITCODE
    }
    "list" {
        docker compose exec -T backend python -m tooling.smoke_data list-runs
        exit $LASTEXITCODE
    }
    "scenarios" {
        docker compose exec -T backend python -m tooling.smoke_data scenarios
        exit $LASTEXITCODE
    }
}
