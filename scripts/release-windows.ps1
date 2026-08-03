param(
    [Parameter(Mandatory = $true)][string]$CertificatePath,
    [Parameter(Mandatory = $true)][string]$Publisher,
    [Parameter(Mandatory = $true)][string]$ShadowReport,
    [Parameter(Mandatory = $true)][string]$LockedAudit,
    [ValidatePattern('^\d+\.\d+\.\d+\.\d+$')][string]$Version = "1.0.0.0",
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$manifestPath = Join-Path $projectRoot "native\SignalDesk.Shell\Package.appxmanifest"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
if ($Publisher -match "Development") { throw "A development publisher cannot sign v1.0." }

& $python -m signaldesk.release_readiness --shadow-report $ShadowReport --locked-audit $LockedAudit
if ($LASTEXITCODE -ne 0) { throw "Release readiness gates are not satisfied." }

$CertificatePath = (Resolve-Path $CertificatePath).Path
$password = Read-Host "PFX password" -AsSecureString
$certificate = New-Object Security.Cryptography.X509Certificates.X509Certificate2(
    $CertificatePath,
    $password,
    [Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet
)
if (-not $certificate.HasPrivateKey) { throw "The production certificate has no private key." }
if ($certificate.Subject -ne $Publisher) {
    throw "Certificate subject '$($certificate.Subject)' does not match Publisher '$Publisher'."
}
if ($certificate.NotAfter -le (Get-Date)) { throw "The production certificate has expired." }

$installed = Import-PfxCertificate -FilePath $CertificatePath -CertStoreLocation Cert:\CurrentUser\My -Password $password
$backupManifest = [IO.File]::ReadAllBytes($manifestPath)
try {
    [xml]$manifest = Get-Content -Raw $manifestPath
    $manifest.Package.Identity.Publisher = $Publisher
    $manifest.Package.Identity.Version = $Version
    $manifest.Save($manifestPath)
    & (Join-Path $PSScriptRoot "build-windows.ps1") -Configuration Release -CertificateThumbprint $installed.Thumbprint
    if ($LASTEXITCODE -ne 0) { throw "Windows package build failed." }
    $package = Get-ChildItem (Join-Path $projectRoot "native\SignalDesk.Shell") -Recurse -File -Filter "*.msix" |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if (-not $package) { throw "The release build did not create an MSIX." }
    $signature = Get-AuthenticodeSignature $package.FullName
    if ($signature.Status -ne "Valid") { throw "MSIX signature is $($signature.Status)." }
    if ($signature.SignerCertificate.Subject -ne $Publisher) { throw "Signed publisher mismatch." }
    if (-not $OutputDirectory) {
        $OutputDirectory = Join-Path $projectRoot "artifacts\release\$Version"
    }
    New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
    $destination = Join-Path $OutputDirectory "SignalDesk-$Version-x64.msix"
    Copy-Item $package.FullName $destination -Force
    $hash = (Get-FileHash $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    [ordered]@{
        version = $Version
        publisher = $Publisher
        sha256 = $hash
        signed = $true
        package = (Split-Path $destination -Leaf)
        created_at = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json | Set-Content (Join-Path $OutputDirectory "release.json") -Encoding UTF8
    Write-Host "Production release created: $destination"
    Write-Host "SHA-256: $hash"
}
finally {
    [IO.File]::WriteAllBytes($manifestPath, $backupManifest)
    if ($installed) { Remove-Item "Cert:\CurrentUser\My\$($installed.Thumbprint)" -ErrorAction SilentlyContinue }
}
