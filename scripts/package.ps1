param(
    [string]$Version = "1.1.0"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host "[1/3] Building executable with PyInstaller..."
$venvActivate = Join-Path $repo ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    throw "Virtual environment activation script not found at $venvActivate"
}

& $venvActivate
pyinstaller --noconfirm --clean --onefile --windowed --name Editorial --collect-all en_core_web_sm editorial.py

Write-Host "[2/3] Updating installer version to $Version..."
$issPath = Join-Path $repo "installer\Editorial.iss"
$iss = Get-Content $issPath -Raw
$newVersionLine = "#define MyAppVersion `"$Version`""
$pattern = '(?m)^\s*#define\s+MyAppVersion\s+"[^"]*"\s*$'
$match = [Regex]::Match($iss, $pattern)
if (-not $match.Success) {
    throw "Could not find MyAppVersion define in $issPath"
}

$currentLine = $match.Value.Trim()
if ($currentLine -eq $newVersionLine) {
    throw "Version must be incremented before build. MyAppVersion is already $Version"
}

$updated = [Regex]::Replace($iss, $pattern, $newVersionLine, 1)
if ($updated -eq $iss) {
    throw "Could not update MyAppVersion in $issPath"
}
Set-Content -Path $issPath -Value $updated -Encoding UTF8

Write-Host "[3/3] Building installer (if Inno Setup is installed)..."
$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Warning "Inno Setup (ISCC.exe) not found. EXE was built, but installer was skipped."
    Write-Host "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php and rerun this script."
    exit 0
}

& $iscc $issPath
Write-Host "Packaging complete. Installer output is in .\\release"
