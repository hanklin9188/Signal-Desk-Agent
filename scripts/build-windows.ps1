param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [string]$CertificatePath = "",
    [string]$CertificatePassword = "",
    [string]$CertificateThumbprint = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
$shellRoot = Join-Path $projectRoot "native\SignalDesk.Shell"
$serviceOutput = Join-Path $shellRoot "service"
Set-Location $projectRoot

if ($CertificatePath -and $CertificateThumbprint) {
    throw "Use either CertificatePath or CertificateThumbprint, not both."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.12 virtual environment creation failed with exit code $LASTEXITCODE."
    }
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed with exit code $LASTEXITCODE." }
& .\.venv\Scripts\python.exe -m pip install -e ".[gmail]" "pyinstaller>=6.11,<7"
if ($LASTEXITCODE -ne 0) {
    throw "Python dependency installation failed with exit code $LASTEXITCODE."
}

if (Test-Path $serviceOutput) {
    Remove-Item -Recurse -Force $serviceOutput
}
New-Item -ItemType Directory -Force -Path $serviceOutput | Out-Null
& .\.venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --onefile `
    --name signaldesk `
    --collect-all signaldesk `
    --distpath $serviceOutput `
    --workpath (Join-Path $projectRoot "build\pyinstaller") `
    --specpath (Join-Path $projectRoot "build") `
    scripts\windows_service_entry.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }

& powershell -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $shellRoot "GenerateAssets.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Package asset generation failed with exit code $LASTEXITCODE."
}

Push-Location $shellRoot
try {
    dotnet restore
    if ($LASTEXITCODE -ne 0) { throw "dotnet restore failed with exit code $LASTEXITCODE." }
    dotnet build -c $Configuration -p:Platform=x64
    if ($LASTEXITCODE -ne 0) { throw "dotnet build failed with exit code $LASTEXITCODE." }

    $publishArgs = @(
        "publish", "-c", $Configuration,
        "-p:Platform=x64",
        "-p:GenerateAppxPackageOnBuild=true",
        "-p:AppxBundle=Always",
        "-p:AppxBundlePlatforms=x64"
    )
    if ($CertificateThumbprint) {
        $publishArgs += "-p:AppxPackageSigningEnabled=true"
        $publishArgs += "-p:PackageCertificateThumbprint=$CertificateThumbprint"
    } elseif ($CertificatePath) {
        $publishArgs += "-p:AppxPackageSigningEnabled=true"
        $publishArgs += "-p:PackageCertificateKeyFile=$CertificatePath"
        if ($CertificatePassword) {
            $publishArgs += "-p:PackageCertificatePassword=$CertificatePassword"
        }
    } else {
        $publishArgs += "-p:AppxPackageSigningEnabled=false"
    }
    & dotnet @publishArgs
    if ($LASTEXITCODE -ne 0) {
        throw "dotnet publish/MSIX packaging failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

Write-Host "SignalDesk Windows package build completed."
Write-Host "MSIX/Appx output: native\SignalDesk.Shell\AppPackages"
