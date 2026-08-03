[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$SourcePath,
    [string]$DestinationPath = "$env:LOCALAPPDATA\SignalDesk\oauth\credentials.json",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$source = (Resolve-Path $SourcePath).Path
$destination = [System.IO.Path]::GetFullPath($DestinationPath)

try {
    $oauth = Get-Content -Raw -Path $source | ConvertFrom-Json
} catch {
    throw "The selected file is not valid JSON. Download the Desktop app OAuth JSON from Google Cloud."
}

if (-not $oauth.installed -or
    [string]::IsNullOrWhiteSpace([string]$oauth.installed.client_id) -or
    [string]::IsNullOrWhiteSpace([string]$oauth.installed.client_secret) -or
    [string]::IsNullOrWhiteSpace([string]$oauth.installed.auth_uri) -or
    [string]::IsNullOrWhiteSpace([string]$oauth.installed.token_uri)) {
    throw "This is not a Google Desktop app OAuth credentials file. Create an OAuth client with application type 'Desktop app'."
}

$destinationDirectory = Split-Path -Parent $destination
if (-not (Test-Path $destinationDirectory)) {
    New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
}

$sameFile = [string]::Equals($source, $destination, [System.StringComparison]::OrdinalIgnoreCase)
if ((Test-Path $destination) -and -not $sameFile) {
    $sameHash = (Get-FileHash $source -Algorithm SHA256).Hash -eq
                (Get-FileHash $destination -Algorithm SHA256).Hash
    if (-not $sameHash -and -not $Force) {
        throw "A different OAuth file already exists at the destination. Re-run with -Force only if you intend to replace it."
    }
}

if (-not $sameFile -and $PSCmdlet.ShouldProcess($destination, "Copy validated OAuth client configuration")) {
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

if ((Test-Path $destination) -and
    $PSCmdlet.ShouldProcess($destination, "Restrict OAuth client configuration file permissions")) {
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $system = [System.Security.Principal.SecurityIdentifier]::new("S-1-5-18")
    $acl = [System.Security.AccessControl.FileSecurity]::new()
    $acl.SetOwner($currentUser)
    $acl.SetAccessRuleProtection($true, $false)
    $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
        $currentUser,
        [System.Security.AccessControl.FileSystemRights]::FullControl,
        [System.Security.AccessControl.AccessControlType]::Allow
    ))
    $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
        $system,
        [System.Security.AccessControl.FileSystemRights]::FullControl,
        [System.Security.AccessControl.AccessControlType]::Allow
    ))
    Set-Acl -LiteralPath $destination -AclObject $acl
}

Write-Host "OAuth client configuration is ready at:"
Write-Host "  $destination"
Write-Host "In SignalDesk, use aliases such as 'personal' and 'nycu'; both accounts can use this same file."
Write-Host "SignalDesk never needs the Gmail account password."
