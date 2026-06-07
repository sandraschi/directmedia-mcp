set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

REPO := justfile_directory()

# List recipes (no private mcp-central-docs dependency)
default:
    @just --list

# Install Python + frontend deps
bootstrap:
    Set-Location "{{REPO}}"; uv sync --project .
    Set-Location "{{REPO}}\web_sota"; npm install

# Full stack via start.bat
serve:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{{REPO}}\web_sota\start.ps1"

serve-backend:
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{{REPO}}\web_sota\start.ps1" -BackendOnly -NoBrowser

# ── Quality ───────────────────────────────────────────────────────────────────

# Execute Ruff SOTA v13.1 linting
lint:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome ci .

# Execute Ruff SOTA v13.1 fix and formatting
fix:
    Set-Location '{{justfile_directory()}}'
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .
    Set-Location '{{justfile_directory()}}\web_sota'
    npx @biomejs/biome check --write .

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit security audit
check-sec:
    Set-Location '{{justfile_directory()}}'
    uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    Set-Location '{{justfile_directory()}}'
    uv run safety check
