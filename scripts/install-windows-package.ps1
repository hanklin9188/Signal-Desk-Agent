[CmdletBinding()]
param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [string]$PackagePath = "",
    [string]$CertificatePath = "$env:LOCALAPPDATA\SignalDesk\certificates\SignalDesk.Development.cer",
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows -and $PSVersionTable.PSVersion.Major -ge 6) {
    throw "This installer must run in Windows PowerShell or PowerShell on Windows."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdministrator) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy Bypass",
        "-File `"$PSCommandPath`"",
        "-Configuration $Configuration"
    )
    if ($PackagePath) { $arguments += "-PackagePath `"$PackagePath`"" }
    if ($CertificatePath) { $arguments += "-CertificatePath `"$CertificatePath`"" }
    if ($NoLaunch) { $arguments += "-NoLaunch" }
    $elevatedProcess = Start-Process powershell.exe -Verb RunAs -ArgumentList ($arguments -join " ") -Wait -PassThru
    exit $elevatedProcess.ExitCode
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($PackagePath)) {
    $packageSearchRoot = Join-Path $projectRoot "native\SignalDesk.Shell\bin\x64\$Configuration"
    if (-not (Test-Path $packageSearchRoot)) {
        throw "No $Configuration package output exists. Run .\scripts\build-windows.ps1 first."
    }
    $package = Get-ChildItem -Path $packageSearchRoot -Recurse -File -Filter "SignalDesk.Shell_*_x64.msix" |
        Where-Object { $_.FullName -notmatch "[\\/]Dependencies[\\/]" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $package) {
        throw "No SignalDesk x64 MSIX package was found under $packageSearchRoot."
    }
    $PackagePath = $package.FullName
} else {
    $PackagePath = (Resolve-Path $PackagePath).Path
}

$CertificatePath = (Resolve-Path $CertificatePath).Path
$publicCertificate = New-Object Security.Cryptography.X509Certificates.X509Certificate2($CertificatePath)
$signature = Get-AuthenticodeSignature -FilePath $PackagePath
if (-not $signature.SignerCertificate) {
    throw "The selected MSIX is not signed. Rebuild it with -CertificateThumbprint."
}
if ($signature.SignerCertificate.Thumbprint -ne $publicCertificate.Thumbprint) {
    throw "The MSIX signer does not match the supplied public certificate."
}

$trustedCertificate = Get-ChildItem Cert:\LocalMachine\TrustedPeople |
    Where-Object { $_.Thumbprint -eq $publicCertificate.Thumbprint } |
    Select-Object -First 1
if (-not $trustedCertificate) {
    Write-Host "Trusting SignalDesk's local development certificate for this computer..."
    Import-Certificate -FilePath $CertificatePath -CertStoreLocation "Cert:\LocalMachine\TrustedPeople" | Out-Null
}

$signature = Get-AuthenticodeSignature -FilePath $PackagePath
if ($signature.Status -ne "Valid") {
    throw "MSIX signature validation failed after certificate installation: $($signature.StatusMessage)"
}

$dependencyDirectory = Join-Path (Split-Path $PackagePath -Parent) "Dependencies\x64"
$dependencies = @()
if (Test-Path $dependencyDirectory) {
    $dependencies = @(Get-ChildItem -Path $dependencyDirectory -File -Filter "*.msix" |
        Select-Object -ExpandProperty FullName)
}

Write-Host "Installing SignalDesk..."
$installArguments = @{
    Path = $PackagePath
    ForceApplicationShutdown = $true
}
if ($dependencies.Count -gt 0) {
    $installArguments.DependencyPath = $dependencies
}
Add-AppxPackage @installArguments

$installedPackage = Get-AppxPackage -Name "SignalDesk.Agent" | Select-Object -First 1
if (-not $installedPackage) {
    throw "Windows did not report SignalDesk as installed."
}

Write-Host "SignalDesk installed successfully."
Write-Host "Version: $($installedPackage.Version)"
Write-Host "Package: $PackagePath"

if (-not $NoLaunch) {
    $appUserModelId = "$($installedPackage.PackageFamilyName)!App"
    Start-Process explorer.exe -ArgumentList "shell:AppsFolder\$appUserModelId"
    Write-Host "SignalDesk launch requested."
}
