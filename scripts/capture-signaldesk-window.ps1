param(
    [string]$OutputPath = "",
    [string]$WindowTitle = "SignalDesk"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class SignalDeskCaptureNative
{
    [StructLayout(LayoutKind.Sequential)]
    public struct Rect
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("dwmapi.dll")]
    public static extern int DwmGetWindowAttribute(
        IntPtr hwnd, int attribute, out Rect value, int size);

    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
}
"@

$process = Get-Process SignalDesk.Shell | Select-Object -First 1
if (-not $process) { throw "SignalDesk process was not found." }
$condition = New-Object Windows.Automation.PropertyCondition(
    [Windows.Automation.AutomationElement]::ProcessIdProperty,
    $process.Id
)
$windows = [Windows.Automation.AutomationElement]::RootElement.FindAll(
    [Windows.Automation.TreeScope]::Children,
    $condition
)
$window = $windows |
    Where-Object {
        $_.Current.Name -eq $WindowTitle -and
        -not $_.Current.BoundingRectangle.IsEmpty
    } |
    Select-Object -First 1
if (-not $window) { throw "SignalDesk window '$WindowTitle' was not found." }

$handle = [IntPtr]$window.Current.NativeWindowHandle
$rect = New-Object SignalDeskCaptureNative+Rect
$result = [SignalDeskCaptureNative]::DwmGetWindowAttribute(
    $handle,
    9,
    [ref]$rect,
    [Runtime.InteropServices.Marshal]::SizeOf($rect)
)
if ($result -ne 0) { throw "DwmGetWindowAttribute failed with HRESULT $result." }
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) { throw "SignalDesk window has invalid bounds." }

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $OutputPath = Join-Path $projectRoot "outputs\signaldesk-window.png"
}
$folder = Split-Path $OutputPath -Parent
if ($folder) { New-Item -ItemType Directory -Force -Path $folder | Out-Null }

$bitmap = New-Object Drawing.Bitmap($width, $height)
$graphics = [Drawing.Graphics]::FromImage($bitmap)
$deviceContext = $graphics.GetHdc()
try {
    if (-not [SignalDeskCaptureNative]::PrintWindow($handle, $deviceContext, 2)) {
        throw "PrintWindow failed."
    }
} finally {
    $graphics.ReleaseHdc($deviceContext)
}
$bitmap.Save($OutputPath, [Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

[pscustomobject]@{
    Path = (Resolve-Path $OutputPath).Path
    Width = $width
    Height = $height
    ProcessId = $process.Id
} | ConvertTo-Json
