[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ManifestPath = "",
    [string]$CertificateDirectory = "$env:LOCALAPPDATA\SignalDesk\certificates"
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    $ManifestPath = Join-Path $PSScriptRoot "..\native\SignalDesk.Shell\Package.appxmanifest"
}
$manifest = (Resolve-Path $ManifestPath).Path
[xml]$manifestXml = Get-Content -Raw -Path $manifest
$publisher = [string]$manifestXml.Package.Identity.Publisher
if ([string]::IsNullOrWhiteSpace($publisher)) {
    throw "The package manifest does not contain an Identity Publisher."
}

$now = Get-Date
$certificate = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object {
        $_.Subject -eq $publisher -and
        $_.HasPrivateKey -and
        $_.NotAfter -gt $now.AddMonths(1) -and
        ($_.EnhancedKeyUsageList.ObjectId.Value -contains "1.3.6.1.5.5.7.3.3")
    } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $certificate) {
    if (-not $PSCmdlet.ShouldProcess($publisher, "Create local development code-signing certificate")) {
        exit 0
    }
    $certificate = New-SelfSignedCertificate `
        -Type Custom `
        -KeyUsage DigitalSignature `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @(
            "2.5.29.37={text}1.3.6.1.5.5.7.3.3",
            "2.5.29.19={text}"
        ) `
        -Subject $publisher `
        -FriendlyName "SignalDesk local development signing" `
        -NotAfter $now.AddYears(2)
}

New-Item -ItemType Directory -Force -Path $CertificateDirectory | Out-Null
$cerPath = Join-Path $CertificateDirectory "SignalDesk.Development.cer"
Export-Certificate -Cert $certificate -FilePath $cerPath -Force | Out-Null

Write-Host "Development certificate ready."
Write-Host "Publisher: $publisher"
Write-Host "Thumbprint: $($certificate.Thumbprint)"
Write-Host "Public certificate: $cerPath"
Write-Host ""
Write-Host "Build the locally installable package with:"
Write-Host "  .\scripts\build-windows.ps1 -Configuration Release -CertificateThumbprint $($certificate.Thumbprint)"
Write-Host "After the build, install it with an administrator prompt:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\install-windows-package.ps1"
Write-Host "This certificate is only for local development and must not be used as a public release identity."
