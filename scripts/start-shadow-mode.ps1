param(
    [string]$DatabasePath = "$env:LOCALAPPDATA\SignalDesk\signaldesk.db",
    [switch]$Reset
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$arguments = @("-m", "signaldesk.shadow_mode", "--database", $DatabasePath, "start")
if ($Reset) { $arguments += "--reset" }
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw "Shadow Mode did not start." }
Write-Host "SignalDesk remains non-interrupting while real decisions and feedback accumulate."
Write-Host "Do not use -Reset unless intentionally restarting the 7-day minimum clock."
