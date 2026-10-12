# Per-repo fleet start config for directmedia-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'directmedia-mcp'
    BackendPort  = 10827
    FrontendPort = 10826
    HealthPath   = '/health'
    WebRoot      = 'web_sota'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'directmedia_mcp.server:app'
        SyncExtras    = @('dev')
        SyncOnStart  = $true
        Env           = @{ WEB_PORT = '10827' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
