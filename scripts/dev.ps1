$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if ($args -contains "--demo") { $env:SIGNALDESK_DEMO = "1" }
& .\.venv\Scripts\signaldesk.exe
