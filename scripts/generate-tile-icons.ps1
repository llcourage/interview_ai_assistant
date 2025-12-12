# Generate Windows Tile Icons from Base Icon
# This script generates all required tile icon sizes for Windows AppX/MSIX packages
# Required sizes: 44x44, 150x150, 310x150, 310x310

param(
    [string]$SourceIcon = "resources\icon.png",
    [string]$OutputDir = "resources\tiles"
)

# Check if source icon exists
if (-not (Test-Path $SourceIcon)) {
    Write-Host "Error: Source icon not found at $SourceIcon" -ForegroundColor Red
    Write-Host "Please ensure resources\icon.png exists" -ForegroundColor Yellow
    exit 1
}

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Created directory: $OutputDir" -ForegroundColor Green
}

# Load System.Drawing assembly
Add-Type -AssemblyName System.Drawing

try {
    # Load the source image
    $sourceImage = [System.Drawing.Image]::FromFile((Resolve-Path $SourceIcon))
    Write-Host "Loaded source icon: $SourceIcon" -ForegroundColor Green
    
    # Function to resize and save image
    function Resize-Image {
        param(
            [System.Drawing.Image]$Image,
            [int]$Width,
            [int]$Height,
            [string]$OutputPath
        )
        
        # Create bitmap with specified size
        $bitmap = New-Object System.Drawing.Bitmap($Width, $Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        
        # High quality resizing
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        
        # Draw resized image
        $graphics.DrawImage($Image, 0, 0, $Width, $Height)
        
        # Save as PNG
        $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        
        # Cleanup
        $graphics.Dispose()
        $bitmap.Dispose()
        
        Write-Host "  ✓ Generated: $OutputPath ($Width x $Height)" -ForegroundColor Cyan
    }
    
    # Generate required tile icons
    Write-Host "`nGenerating Windows tile icons..." -ForegroundColor Yellow
    
    # StoreLogo.png - Store logo (50x50)
    Resize-Image -Image $sourceImage -Width 50 -Height 50 -OutputPath "$OutputDir\StoreLogo.png"
    
    # Square44x44Logo.png - Taskbar icon
    Resize-Image -Image $sourceImage -Width 44 -Height 44 -OutputPath "$OutputDir\Square44x44Logo.png"
    
    # Square150x150Logo.png - Small tile
    Resize-Image -Image $sourceImage -Width 150 -Height 150 -OutputPath "$OutputDir\Square150x150Logo.png"
    
    # Wide310x150Logo.png - Wide tile
    Resize-Image -Image $sourceImage -Width 310 -Height 150 -OutputPath "$OutputDir\Wide310x150Logo.png"
    
    # Square310x310Logo.png - Large tile
    Resize-Image -Image $sourceImage -Width 310 -Height 310 -OutputPath "$OutputDir\Square310x310Logo.png"
    
    # Cleanup
    $sourceImage.Dispose()
    
    Write-Host "`n✅ All tile icons generated successfully!" -ForegroundColor Green
    Write-Host "   Location: $OutputDir" -ForegroundColor Cyan
    Write-Host "`nNote: These icons must uniquely represent your product." -ForegroundColor Yellow
    Write-Host "      Ensure they are distinct and recognizable." -ForegroundColor Yellow
    
} catch {
    Write-Host "Error generating tile icons: $_" -ForegroundColor Red
    exit 1
}



