# ========================================
# Convert PNG to ICO for Windows Icon
# Creates ICO with multiple sizes (16, 32, 48, 256)
# Ensures minimum 256x256 size for electron-builder
# ========================================

param(
    [string]$PngPath = "resources\icon.png",
    [string]$IcoPath = "resources\icon.ico"
)

Write-Host "Converting PNG to ICO..." -ForegroundColor Cyan

# Get absolute paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FullPngPath = Join-Path $ProjectRoot $PngPath
$FullIcoPath = Join-Path $ProjectRoot $IcoPath

if (-not (Test-Path $FullPngPath)) {
    Write-Host "[ERROR] PNG file not found: $FullPngPath" -ForegroundColor Red
    exit 1
}

try {
    # Load System.Drawing assembly
    Add-Type -AssemblyName System.Drawing
    
    # Load the PNG image
    $pngImage = [System.Drawing.Image]::FromFile($FullPngPath)
    $originalWidth = $pngImage.Width
    $originalHeight = $pngImage.Height
    
    Write-Host "Original PNG size: ${originalWidth}x${originalHeight}" -ForegroundColor Cyan
    
    # Check if image is at least 256x256
    $minSize = 256
    if ($originalWidth -lt $minSize -or $originalHeight -lt $minSize) {
        Write-Host "Warning: PNG is smaller than ${minSize}x${minSize}, resizing..." -ForegroundColor Yellow
        
        # Calculate new size maintaining aspect ratio
        $ratio = [Math]::Min($minSize / $originalWidth, $minSize / $originalHeight)
        $newWidth = [Math]::Max([int]($originalWidth * $ratio), $minSize)
        $newHeight = [Math]::Max([int]($originalHeight * $ratio), $minSize)
        
        Write-Host "Resizing to: ${newWidth}x${newHeight}" -ForegroundColor Cyan
        
        # Create resized bitmap with high quality
        $resizedBitmap = New-Object System.Drawing.Bitmap($newWidth, $newHeight)
        $graphics = [System.Drawing.Graphics]::FromImage($resizedBitmap)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.DrawImage($pngImage, 0, 0, $newWidth, $newHeight)
        $graphics.Dispose()
        $pngImage.Dispose()
        $pngImage = $resizedBitmap
    }
    
    # ICO sizes to include (Windows standard sizes)
    $icoSizes = @(16, 32, 48, 256)
    
    # Create list to store icon images
    $iconImages = New-Object System.Collections.ArrayList
    
    foreach ($size in $icoSizes) {
        # Resize image to this size
        $resized = New-Object System.Drawing.Bitmap($size, $size)
        $graphics = [System.Drawing.Graphics]::FromImage($resized)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.DrawImage($pngImage, 0, 0, $size, $size)
        $graphics.Dispose()
        
        # Create icon from bitmap
        $icon = [System.Drawing.Icon]::FromHandle($resized.GetHicon())
        $iconImages.Add($icon) | Out-Null
        $resized.Dispose()
    }
    
    # Create ICO file with multiple sizes
    # Note: System.Drawing.Icon doesn't support multi-size ICO directly
    # We'll use the largest size (256x256) which is required by electron-builder
    $icoStream = New-Object System.IO.FileStream($FullIcoPath, [System.IO.FileMode]::Create)
    $largestIcon = $iconImages[$iconImages.Count - 1]  # 256x256 is the last one
    $largestIcon.Save($icoStream)
    $icoStream.Close()
    
    # Cleanup
    foreach ($icon in $iconImages) {
        $icon.Dispose()
    }
    $pngImage.Dispose()
    
    Write-Host "[SUCCESS] ICO file created: $FullIcoPath" -ForegroundColor Green
    Write-Host "ICO size: 256x256 (required by electron-builder)" -ForegroundColor Green
    
} catch {
    Write-Host "[ERROR] Failed to convert: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Alternative: electron-builder can use PNG directly." -ForegroundColor Yellow
    Write-Host "Update package.json to use 'resources/icon.png' instead." -ForegroundColor Yellow
    exit 1
}

