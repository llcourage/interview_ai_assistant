# ========================================
# Install MSIX Certificate to Trusted Root CA
# ========================================
# This script installs the self-signed certificate to Local Machine's
# Trusted Root Certification Authorities store
# Run this script as Administrator

param(
    [string]$CertPath = "",
    [string]$CertDir = "certificates"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Install MSIX Certificate to Trusted Root CA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Get project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Find certificate file
if ([string]::IsNullOrEmpty($CertPath)) {
    # Try to find .cer file in certificates directory
    $CertDirPath = Join-Path $ProjectRoot $CertDir
    $CertFiles = Get-ChildItem -Path $CertDirPath -Filter "*.cer" -ErrorAction SilentlyContinue
    
    if ($CertFiles.Count -eq 0) {
        # Try dist-electron directory (where electron-builder might put it)
        $DistElectronPath = Join-Path $ProjectRoot "dist-electron"
        $CertFiles = Get-ChildItem -Path $DistElectronPath -Filter "*.cer" -ErrorAction SilentlyContinue
    }
    
    if ($CertFiles.Count -eq 0) {
        Write-Host "[ERROR] No .cer certificate file found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please either:" -ForegroundColor Yellow
        Write-Host "  1. Run: scripts\generate-certificate.ps1" -ForegroundColor White
        Write-Host "  2. Or specify the certificate path:" -ForegroundColor White
        Write-Host "     .\install-certificate.ps1 -CertPath 'path\to\certificate.cer'" -ForegroundColor Gray
        exit 1
    }
    
    if ($CertFiles.Count -gt 1) {
        Write-Host "[INFO] Multiple certificate files found:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $CertFiles.Count; $i++) {
            Write-Host "  [$($i+1)] $($CertFiles[$i].FullName)" -ForegroundColor Gray
        }
        $choice = Read-Host "Select certificate number (1-$($CertFiles.Count))"
        $CertPath = $CertFiles[[int]$choice - 1].FullName
    } else {
        $CertPath = $CertFiles[0].FullName
    }
}

if (-not (Test-Path $CertPath)) {
    Write-Host "[ERROR] Certificate file not found: $CertPath" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Using certificate: $CertPath" -ForegroundColor Green
Write-Host ""

Write-Host "[1/2] Importing certificate to Local Machine..." -ForegroundColor Yellow

try {
    # Import certificate to Local Machine's Trusted Root Certification Authorities
    $cert = Import-Certificate `
        -FilePath $CertPath `
        -CertStoreLocation "Cert:\LocalMachine\Root"
    
    if ($null -eq $cert) {
        Write-Host "[ERROR] Failed to import certificate" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "[SUCCESS] Certificate imported successfully!" -ForegroundColor Green
    Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
    Write-Host "  Subject: $($cert.Subject)" -ForegroundColor Gray
    Write-Host "  Store: Trusted Root Certification Authorities (Local Machine)" -ForegroundColor Gray
    
} catch {
    Write-Host "[ERROR] Failed to import certificate: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/2] Verifying certificate installation..." -ForegroundColor Yellow

# Verify the certificate is in the store
$installedCert = Get-ChildItem -Path "Cert:\LocalMachine\Root" | Where-Object { $_.Thumbprint -eq $cert.Thumbprint }
if ($null -ne $installedCert) {
    Write-Host "[SUCCESS] Certificate verified in Trusted Root CA store!" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Certificate may not be properly installed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Certificate installation complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now install MSIX packages without certificate errors." -ForegroundColor Green
Write-Host ""
Write-Host "To test:" -ForegroundColor Yellow
Write-Host "  1. Double-click your .msix or .appx file" -ForegroundColor White
Write-Host "  2. It should install without the 0x800B010A error" -ForegroundColor White
Write-Host ""






