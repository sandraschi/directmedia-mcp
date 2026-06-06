Param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$NoBrowser
)

$WebStart = Join-Path $PSScriptRoot "web_sota\start.ps1"
if (-not (Test-Path $WebStart)) {
    Write-Host "ERROR: Missing web_sota start script at $WebStart" -ForegroundColor Red
    exit 1
}

& $WebStart @PSBoundParameters
exit $LASTEXITCODE
