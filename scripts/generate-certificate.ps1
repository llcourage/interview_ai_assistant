# ========================================
# Generate Self-Signed Certificate for MSIX
# ========================================
# This script generates a self-signed certificate for signing MSIX packages
# Run this script as Administrator

param(
    [string]$CertName = "DesktopAI_MSIX_Certificate",
    [string]$OutputDir = "certificates"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Generate Self-Signed Certificate for MSIX" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Get project root (assuming script is in scripts/ folder)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$CertDir = Join-Path $ProjectRoot $OutputDir

# Create certificates directory if it doesn't exist
if (-not (Test-Path $CertDir)) {
    New-Item -ItemType Directory -Path $CertDir -Force | Out-Null
    Write-Host "[INFO] Created certificates directory: $CertDir" -ForegroundColor Green
}

# Certificate file paths
$CertPfx = Join-Path $CertDir "$CertName.pfx"
$CertCer = Join-Path $CertDir "$CertName.cer"
$Password = "DesktopAI2024!"  # Change this to a secure password

Write-Host "[1/3] Generating self-signed certificate..." -ForegroundColor Yellow

# Generate certificate
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=Desktop AI, O=InvestAI Labs LLC" `
    -KeyUsage DigitalSignature `
    -FriendlyName "Desktop AI MSIX Certificate" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -KeyExportPolicy Exportable `
    -NotAfter (Get-Date).AddYears(5) `
    -KeySpec Signature

if ($null -eq $cert) {
    Write-Host "[ERROR] Failed to generate certificate" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Certificate generated successfully!" -ForegroundColor Green
Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
Write-Host "  Subject: $($cert.Subject)" -ForegroundColor Gray

Write-Host "[2/3] Exporting certificate to PFX file..." -ForegroundColor Yellow

# Export to PFX (for signing)
$SecurePassword = ConvertTo-SecureString -String $Password -Force -AsPlainText
Export-PfxCertificate `
    -Cert $cert `
    -FilePath $CertPfx `
    -Password $SecurePassword | Out-Null

if (Test-Path $CertPfx) {
    Write-Host "[SUCCESS] PFX certificate exported: $CertPfx" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to export PFX certificate" -ForegroundColor Red
    exit 1
}

Write-Host "[3/3] Exporting certificate to CER file..." -ForegroundColor Yellow

# Export to CER (for installation)
Export-Certificate `
    -Cert $cert `
    -FilePath $CertCer | Out-Null

if (Test-Path $CertCer) {
    Write-Host "[SUCCESS] CER certificate exported: $CertCer" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to export CER certificate" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Certificate generation complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Certificate files:" -ForegroundColor Yellow
Write-Host "  PFX: $CertPfx" -ForegroundColor Gray
Write-Host "  CER: $CertCer" -ForegroundColor Gray
Write-Host ""
Write-Host "Certificate password: $Password" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run: scripts\install-certificate.ps1" -ForegroundColor White
Write-Host "     (This will install the certificate to Trusted Root CA)" -ForegroundColor Gray
Write-Host "  2. Update package.json to use this certificate for signing" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  IMPORTANT: Keep the PFX file and password secure!" -ForegroundColor Red
Write-Host ""







