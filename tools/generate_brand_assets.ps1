Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$brandDir = Join-Path $root "custom_components\bom_weather\brand"
New-Item -ItemType Directory -Force -Path $brandDir | Out-Null

function New-Canvas {
    param(
        [int] $Width,
        [int] $Height
    )

    $bitmap = New-Object System.Drawing.Bitmap $Width, $Height
    $bitmap.SetResolution(96, 96)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.Clear([System.Drawing.Color]::Transparent)

    return [pscustomobject]@{
        Bitmap = $bitmap
        Graphics = $graphics
    }
}

function New-LinearBrush {
    param(
        [System.Drawing.RectangleF] $Bounds,
        [System.Drawing.Color] $Start,
        [System.Drawing.Color] $End,
        [float] $Angle
    )

    return New-Object System.Drawing.Drawing2D.LinearGradientBrush $Bounds, $Start, $End, $Angle
}

function Fill-RoundedRectangle {
    param(
        [System.Drawing.Graphics] $Graphics,
        [System.Drawing.Brush] $Brush,
        [System.Drawing.RectangleF] $Bounds,
        [float] $Radius
    )

    $diameter = $Radius * 2
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc($Bounds.X, $Bounds.Y, $diameter, $diameter, 180, 90)
    $path.AddArc($Bounds.Right - $diameter, $Bounds.Y, $diameter, $diameter, 270, 90)
    $path.AddArc($Bounds.Right - $diameter, $Bounds.Bottom - $diameter, $diameter, $diameter, 0, 90)
    $path.AddArc($Bounds.X, $Bounds.Bottom - $diameter, $diameter, $diameter, 90, 90)
    $path.CloseFigure()
    $Graphics.FillPath($Brush, $path)
    $path.Dispose()
}

function Draw-WeatherMark {
    param(
        [System.Drawing.Graphics] $Graphics,
        [float] $X,
        [float] $Y,
        [float] $Size
    )

    $blue = [System.Drawing.Color]::FromArgb(255, 13, 99, 153)
    $lightBlue = [System.Drawing.Color]::FromArgb(255, 73, 183, 214)
    $yellow = [System.Drawing.Color]::FromArgb(255, 255, 194, 71)
    $white = [System.Drawing.Color]::FromArgb(255, 255, 255, 255)

    $circleBounds = New-Object System.Drawing.RectangleF $X, $Y, $Size, $Size
    $skyBrush = New-LinearBrush $circleBounds $lightBlue $blue 135
    $Graphics.FillEllipse($skyBrush, $circleBounds)
    $skyBrush.Dispose()

    $sunBrush = New-Object System.Drawing.SolidBrush $yellow
    $sunSize = $Size * 0.27
    $Graphics.FillEllipse(
        $sunBrush,
        $X + ($Size * 0.16),
        $Y + ($Size * 0.15),
        $sunSize,
        $sunSize
    )
    $sunBrush.Dispose()

    $cloudBrush = New-Object System.Drawing.SolidBrush $white
    $Graphics.FillEllipse($cloudBrush, $X + ($Size * 0.23), $Y + ($Size * 0.45), $Size * 0.25, $Size * 0.21)
    $Graphics.FillEllipse($cloudBrush, $X + ($Size * 0.37), $Y + ($Size * 0.35), $Size * 0.31, $Size * 0.31)
    $Graphics.FillEllipse($cloudBrush, $X + ($Size * 0.56), $Y + ($Size * 0.47), $Size * 0.23, $Size * 0.19)
    $Graphics.FillRectangle($cloudBrush, $X + ($Size * 0.32), $Y + ($Size * 0.54), $Size * 0.42, $Size * 0.12)
    $cloudBrush.Dispose()

    $wavePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(230, 255, 255, 255)), ($Size * 0.035)
    $wavePen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $wavePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    for ($i = 0; $i -lt 3; $i++) {
        $path = New-Object System.Drawing.Drawing2D.GraphicsPath
        $yWave = $Y + ($Size * (0.73 + ($i * 0.085)))
        $path.AddBezier(
            $X + ($Size * 0.22),
            $yWave,
            $X + ($Size * 0.34),
            $yWave - ($Size * 0.06),
            $X + ($Size * 0.44),
            $yWave + ($Size * 0.06),
            $X + ($Size * 0.56),
            $yWave
        )
        $path.AddBezier(
            $X + ($Size * 0.56),
            $yWave,
            $X + ($Size * 0.66),
            $yWave - ($Size * 0.06),
            $X + ($Size * 0.76),
            $yWave + ($Size * 0.06),
            $X + ($Size * 0.86),
            $yWave
        )
        $Graphics.DrawPath($wavePen, $path)
        $path.Dispose()
    }
    $wavePen.Dispose()
}

function Save-Icon {
    param(
        [int] $Size,
        [string] $Path
    )

    $canvas = New-Canvas $Size $Size
    $graphics = $canvas.Graphics

    $bgBounds = New-Object System.Drawing.RectangleF 0, 0, $Size, $Size
    $bgBrush = New-LinearBrush $bgBounds `
        ([System.Drawing.Color]::FromArgb(255, 5, 47, 78)) `
        ([System.Drawing.Color]::FromArgb(255, 32, 145, 177)) 135
    Fill-RoundedRectangle $graphics $bgBrush $bgBounds ($Size * 0.18)
    $bgBrush.Dispose()

    Draw-WeatherMark $graphics ($Size * 0.14) ($Size * 0.14) ($Size * 0.72)

    $canvas.Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $canvas.Bitmap.Dispose()
}

function Save-Logo {
    param(
        [int] $Width,
        [int] $Height,
        [string] $Path
    )

    $canvas = New-Canvas $Width $Height
    $graphics = $canvas.Graphics

    $markSize = $Height * 0.68
    Draw-WeatherMark $graphics ($Height * 0.16) (($Height - $markSize) / 2) $markSize

    $textBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 6, 56, 84))
    $subBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 72, 95, 112))
    $font = New-Object System.Drawing.Font "Segoe UI", ($Height * 0.21), ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
    $subFont = New-Object System.Drawing.Font "Segoe UI", ($Height * 0.095), ([System.Drawing.FontStyle]::Regular), ([System.Drawing.GraphicsUnit]::Pixel)

    $textX = $Height * 0.96
    $graphics.DrawString("BOM Weather", $font, $textBrush, $textX, $Height * 0.24)
    $graphics.DrawString("Home Assistant integration", $subFont, $subBrush, $textX + 2, $Height * 0.53)

    $font.Dispose()
    $subFont.Dispose()
    $textBrush.Dispose()
    $subBrush.Dispose()

    $canvas.Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $canvas.Bitmap.Dispose()
}

Save-Icon 256 (Join-Path $brandDir "icon.png")
Save-Icon 512 (Join-Path $brandDir "icon@2x.png")
Save-Logo 768 256 (Join-Path $brandDir "logo.png")
Save-Logo 1536 512 (Join-Path $brandDir "logo@2x.png")
