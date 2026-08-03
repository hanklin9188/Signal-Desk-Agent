param(
    [Parameter(Mandatory = $true)][string]$PackagePath,
    [string]$ExpectedPublisher = "",
    [switch]$Launch
)

$ErrorActionPreference = "Stop"
$PackagePath = (Resolve-Path $PackagePath).Path
$signature = Get-AuthenticodeSignature $PackagePath
if ($signature.Status -ne "Valid") { throw "Package signature is $($signature.Status)." }
if ($ExpectedPublisher -and $signature.SignerCertificate.Subject -ne $ExpectedPublisher) {
    throw "Package publisher does not match the expected publisher."
}
$current = Get-AppxPackage -Name "SignalDesk.Agent" | Select-Object -First 1
$backupRoot = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "SignalDeskBackups"
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$backup = Join-Path $backupRoot $stamp
$data = Join-Path $env:LOCALAPPDATA "SignalDesk"
if (Test-Path $data) {
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    Copy-Item $data (Join-Path $backup "SignalDesk") -Recurse -Force
}
Write-Host "Current version: $($current.Version)"
Write-Host "Recoverable data backup: $backup"
Add-AppxPackage -Path $PackagePath -ForceApplicationShutdown -ForceUpdateFromAnyVersion
$installed = Get-AppxPackage -Name "SignalDesk.Agent" | Select-Object -First 1
if (-not $installed) { throw "SignalDesk was not installed after the package operation." }
Write-Host "Installed version: $($installed.Version)"
if ($Launch) {
    Start-Process "shell:AppsFolder\$($installed.PackageFamilyName)!App"
}
