[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$SkipWinUIWorkload
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE."
    }
}

function Show-EnvironmentStatus {
    Write-Host "SignalDesk Windows prerequisite status"
    $python = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source -3.12 --version
    } else {
        Write-Warning "Python launcher was not found. Install Python 3.12 x64."
    }

    $dotnet = Get-Command dotnet.exe -ErrorAction SilentlyContinue
    if ($dotnet) {
        $sdks = @(& $dotnet.Source --list-sdks)
        if ($sdks -match '^8\.') {
            Write-Host ".NET 8 SDK: ready"
        } else {
            Write-Warning ".NET 8 SDK is missing. A runtime alone cannot compile SignalDesk."
        }
    } else {
        Write-Warning "dotnet.exe was not found."
    }

    $vswherePaths = @(
        @(
            (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"),
            (Join-Path $env:ProgramFiles "Microsoft Visual Studio\Installer\vswhere.exe")
        ) | Where-Object { $_ -and (Test-Path $_) }
    )
    if ($vswherePaths.Count -gt 0) {
        $installation = & $($vswherePaths[0]) -latest -products * -property installationPath
        Write-Host "Visual Studio: $installation"
    } else {
        Write-Warning "Visual Studio / WinUI workload was not detected."
    }

    $sdkRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10"
    if (Test-Path $sdkRoot) {
        Write-Host "Windows SDK: $sdkRoot"
    } else {
        Write-Warning "Windows SDK was not detected."
    }
}

if (-not $Install) {
    Show-EnvironmentStatus
    Write-Host ""
    Write-Host "Audit only. To install the missing official prerequisites, run:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows-prerequisites.ps1 -Install"
    exit 0
}

$winget = Get-Command winget.exe -ErrorAction SilentlyContinue
if (-not $winget) {
    throw "WinGet is required. Install or update Microsoft App Installer, then run this script again."
}

Invoke-Checked $winget.Source @(
    "install", "--exact", "--id", "Microsoft.DotNet.SDK.8", "--source", "winget",
    "--accept-package-agreements", "--accept-source-agreements"
)

Invoke-Checked $winget.Source @(
    "install", "--exact", "--id", "Microsoft.WindowsSDK.10.0.26100", "--source", "winget",
    "--accept-package-agreements", "--accept-source-agreements"
)

if (-not $SkipWinUIWorkload) {
    Write-Host "Applying Microsoft's current WinUI development configuration."
    Write-Host "Windows may request elevation and Visual Studio components can take several GB."
    Invoke-Checked $winget.Source @(
        "configure", "-f", "https://aka.ms/winui-config"
    )
}

Show-EnvironmentStatus
Write-Host "Prerequisite setup finished. Open a new PowerShell window before building."
