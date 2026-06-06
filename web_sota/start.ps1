param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$NoBrowser
)

$WebPort = 10826
$BackendPort = 10827
$ProjectRoot = Split-Path -Parent $PSScriptRoot

. "D:/Dev/repos/mcp-central-docs/standards/FleetStartMode.ps1"
$FleetStart = Initialize-FleetStartMode @PSBoundParameters
Enter-FleetHeadlessConsole -Headless:$Headless -BackendOnly:$BackendOnly
Stop-FleetPortSquatters -Ports @($WebPort, $BackendPort) -Label "directmedia-mcp"

Set-Location $ProjectRoot
Write-Host "Syncing Python dependencies ..." -ForegroundColor Cyan
uv sync --project $ProjectRoot
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: uv sync failed for directmedia-mcp." -ForegroundColor Red
    exit 1
}

Set-Location $PSScriptRoot
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies ..." -ForegroundColor Cyan
    npm install
}

Write-Host "Starting Directmedia MCP backend on port $BackendPort ..." -ForegroundColor Cyan
$backendCmd = @"
Set-Location '$ProjectRoot'
uv run --project '$ProjectRoot' uvicorn directmedia_mcp.server:app --host 127.0.0.1 --port $BackendPort --log-level info
if (`$LASTEXITCODE -ne 0) {
  Write-Host 'Backend exited with error. See messages above.' -ForegroundColor Red
  pause
}
"@
Start-Process pwsh -ArgumentList "-NoProfile", "-WindowStyle", "Normal", "-Command", $backendCmd

$healthUrl = "http://127.0.0.1:$BackendPort/health"
$backendReady = $false
Write-Host "Waiting for backend" -ForegroundColor Yellow -NoNewline
for ($attempt = 0; $attempt -lt 45; $attempt++) {
    try {
        $null = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $backendReady = $true
        break
    } catch {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }
}
Write-Host ""

if ($backendReady) {
    Write-Host "Backend ready at $healthUrl" -ForegroundColor Green
} else {
    Write-Host "ERROR: Backend did not respond on $healthUrl within 90s. Check the backend window." -ForegroundColor Red
    exit 1
}

if (-not $FleetStart.RunFrontend) {
    while ($true) { Start-Sleep -Seconds 60 }
}

if (-not $NoBrowser) {
    $frontendUrl = "http://127.0.0.1:$WebPort/"
    $pollAndOpen = "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep -Seconds 1 } }"
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command", $pollAndOpen
}

Write-Host "Starting Vite frontend on port $WebPort (Ctrl+C to stop) ..." -ForegroundColor Green
npm run dev -- --port $WebPort --host 127.0.0.1 --strictPort
