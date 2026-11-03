# Start backend (port 8000) and frontend (port 5173). Close the window or press Ctrl+C to stop.
# Mock mode with no key: $env:MOCK_MODE = 'true'; .\scripts\dev.ps1
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv\Scripts\Activate.ps1'
if (Test-Path $venv) { . $venv }
$backend = Start-Process -PassThru -NoNewWindow -WorkingDirectory (Join-Path $root 'backend') uvicorn 'main:app --reload --port 8000'
try { Set-Location (Join-Path $root 'frontend'); npm run dev } finally { Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue }
