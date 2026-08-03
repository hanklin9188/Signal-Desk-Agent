$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$assetDir = Join-Path $PSScriptRoot "Assets"
New-Item -ItemType Directory -Force -Path $assetDir | Out-Null

function New-SignalDeskLogo {
    param([string]$Name, [int]$Width, [int]$Height)
    $bitmap = [System.Drawing.Bitmap]::new($Width, $Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $rect = [System.Drawing.Rectangle]::new(0, 0, $Width, $Height)
    $start = [System.Drawing.Color]::FromArgb(255, 126, 113, 232)
    $finish = [System.Drawing.Color]::FromArgb(255, 60, 65, 155)
    $brush = [System.Drawing.Drawing2D.LinearGradientBrush]::new($rect, $start, $finish, 135)
    $graphics.FillRectangle($brush, $rect)
    $fontSize = [Math]::Max(12, [Math]::Min($Width, $Height) * 0.42)
    $font = [System.Drawing.Font]::new("Segoe UI", $fontSize, [System.Drawing.FontStyle]::Bold)
    $format = [System.Drawing.StringFormat]::new()
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $layout = [System.Drawing.RectangleF]::new(0, 0, [single]$Width, [single]$Height)
    $graphics.DrawString("S", $font, [System.Drawing.Brushes]::White, $layout, $format)
    $bitmap.Save((Join-Path $assetDir $Name), [System.Drawing.Imaging.ImageFormat]::Png)
    $format.Dispose(); $font.Dispose(); $brush.Dispose(); $graphics.Dispose(); $bitmap.Dispose()
}

New-SignalDeskLogo "StoreLogo.png" 50 50
New-SignalDeskLogo "Square44x44Logo.png" 44 44
New-SignalDeskLogo "Square71x71Logo.png" 71 71
New-SignalDeskLogo "Square150x150Logo.png" 150 150
New-SignalDeskLogo "Wide310x150Logo.png" 310 150
