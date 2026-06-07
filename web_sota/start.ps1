param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$NoBrowser
)

$WebPort = 10826
$BackendPort = 10827
$WebRoot = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $WebRoot

. "D:/Dev/repos/mcp-central-docs/standards/FleetStartMode.ps1"
$FleetStart = Initialize-FleetStartMode @PSBoundParameters
Enter-FleetHeadlessConsole -Headless:$Headless -BackendOnly:$BackendOnly
Stop-FleetPortSquatters -Ports @($WebPort, $BackendPort) -Label "directmedia-mcp"
if (-not (Assert-FleetPortsAvailable -Ports @($WebPort, $BackendPort) -Label "directmedia-mcp")) {
    exit 1
}

$uvExe = (Get-Command uv -ErrorAction Stop).Source

Write-Host ""
Write-Host "Directmedia MCP - Setup and Start" -ForegroundColor Cyan
Write-Host "Backend :$BackendPort   Frontend :$WebPort" -ForegroundColor DarkGray
Write-Host ""

Set-Location $ProjectRoot
Write-Host "[1/4] Syncing Python dependencies ..." -ForegroundColor Cyan
& $uvExe sync --project $ProjectRoot
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: uv sync failed for directmedia-mcp." -ForegroundColor Red
    exit 1
}

Write-Host "  Smoke-testing import ..." -ForegroundColor DarkGray
& $uvExe run --project $ProjectRoot python -c "from directmedia_mcp.server import app; print('  [ok] Import OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: import check failed - see output above." -ForegroundColor Red
    exit 1
}

if ($FleetStart.RunFrontend) {
    Set-Location $WebRoot
    Write-Host "[2/4] Frontend dependencies ..." -ForegroundColor Cyan
    if (-not (Test-Path "node_modules")) {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: npm install failed." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  [ok] node_modules present" -ForegroundColor DarkGreen
    }
}

Write-Host "[3/4] Starting backend on port $BackendPort ..." -ForegroundColor Cyan
$backendLog = Join-Path $ProjectRoot "backend.log"
$backendErr = Join-Path $ProjectRoot "backend.err.log"
foreach ($logPath in @($backendLog, $backendErr)) {
    if (Test-Path -LiteralPath $logPath) {
        Remove-Item -LiteralPath $logPath -Force -ErrorAction SilentlyContinue
    }
}

$backendProc = Start-Process -FilePath $uvExe `
    -ArgumentList @(
        "run", "--project", $ProjectRoot,
        "uvicorn", "directmedia_mcp.server:app",
        "--host", "127.0.0.1",
        "--port", "$BackendPort",
        "--log-level", "info"
    ) `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError $backendErr `
    -PassThru `
    -WindowStyle $(if ($Headless) { "Hidden" } else { "Normal" })

Write-Host "  Backend PID $($backendProc.Id)  (log: $backendLog)" -ForegroundColor DarkGray

$healthUrl = "http://127.0.0.1:$BackendPort/health"
$maxWait = 90
$waited = 0
$backendReady = $false
Write-Host "[4/4] Waiting for backend health (max ${maxWait}s) ..." -ForegroundColor Yellow
while ($waited -lt $maxWait) {
    if ($backendProc.HasExited) {
        Write-Host "ERROR: backend process exited (code $($backendProc.ExitCode))." -ForegroundColor Red
        break
    }
    try {
        $null = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $backendReady = $true
        break
    } catch {
        Start-Sleep -Seconds 1
        $waited++
        if (($waited % 15) -eq 0) {
            Write-Host "    ... ${waited}s" -ForegroundColor DarkGray
        }
    }
}

if (-not $backendReady) {
    Write-Host "ERROR: Backend did not respond on $healthUrl within ${maxWait}s." -ForegroundColor Red
    if (Test-Path -LiteralPath $backendLog) {
        Write-Host "Last lines from backend.log:" -ForegroundColor Yellow
        Get-Content -LiteralPath $backendLog -Tail 30
    }
    if (Test-Path -LiteralPath $backendErr) {
        Write-Host "stderr:" -ForegroundColor Yellow
        Get-Content -LiteralPath $backendErr -Tail 20
    }
    Write-Host "Run directly to see the full error:" -ForegroundColor Yellow
    Write-Host "  Set-Location '$ProjectRoot'; $uvExe run --project '$ProjectRoot' uvicorn directmedia_mcp.server:app --host 127.0.0.1 --port $BackendPort" -ForegroundColor Yellow
    exit 1
}

Write-Host "  [ok] Backend ready at $healthUrl" -ForegroundColor Green

if (-not $FleetStart.RunFrontend) {
    Write-Host ""
    Write-Host "Backend-only mode. Press Ctrl+C to stop." -ForegroundColor Cyan
    try { Wait-Process -Id $backendProc.Id -ErrorAction SilentlyContinue } catch {}
    exit 0
}

Set-Location $WebRoot
if (-not $FleetStart.SkipBrowser) {
    $frontendUrl = "http://127.0.0.1:$WebPort/"
    $pollAndOpen = "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep -Seconds 1 } }"
    Start-Process powershell.exe -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command", $pollAndOpen
}

Write-Host "Starting Vite frontend on port $WebPort (Ctrl+C to stop) ..." -ForegroundColor Green
npm run dev -- --port $WebPort --host 127.0.0.1 --strictPort
