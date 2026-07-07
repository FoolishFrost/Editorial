param(
    [string]$Version = "1.2.2"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host "[1/4] Building executable with PyInstaller..."
$venvActivate = Join-Path $repo ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    throw "Virtual environment activation script not found at $venvActivate"
}

& $venvActivate
pyinstaller --noconfirm --clean --onefile --windowed --name Editorial --collect-all en_core_web_sm --collect-all pyspellchecker editorial.py

Write-Host "[2/4] Creating portable ZIP package and extracting dictionary..."
$distExe = Join-Path $repo "dist\Editorial.exe"
if (-not (Test-Path $distExe)) {
    throw "Expected executable not found at $distExe"
}

# Extract and decompress the spellchecker dictionary
$distDict = Join-Path $repo "dist\dictionary.json"
python -c "import gzip, json, pkgutil, os; data = pkgutil.get_data('spellchecker', 'resources/en.json.gz'); open(r'$distDict', 'w', encoding='utf-8').write(json.dumps(json.loads(gzip.decompress(data).decode('utf-8')), indent=2))"
if (-not (Test-Path $distDict)) {
    Write-Warning "Could not extract dictionary.json from spellchecker"
}

# Copy cliches.txt and redundancies.txt to dist/
Copy-Item -Path (Join-Path $repo "cliches.txt") -Destination (Join-Path $repo "dist\cliches.txt") -Force
Copy-Item -Path (Join-Path $repo "redundancies.txt") -Destination (Join-Path $repo "dist\redundancies.txt") -Force

$releaseDir = Join-Path $repo "release"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

$portableZip = Join-Path $releaseDir ("Editorial-{0}-portable.zip" -f $Version)
if (Test-Path $portableZip) {
    Remove-Item -Path $portableZip -Force
}

$portableStage = Join-Path $releaseDir ("portable-{0}" -f $Version)
if (Test-Path $portableStage) {
    Remove-Item -Path $portableStage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $portableStage | Out-Null
Copy-Item -Path $distExe -Destination (Join-Path $portableStage "Editorial.exe") -Force
if (Test-Path $distDict) {
    Copy-Item -Path $distDict -Destination (Join-Path $portableStage "dictionary.json") -Force
}
$distCliches = Join-Path $repo "dist\cliches.txt"
if (Test-Path $distCliches) {
    Copy-Item -Path $distCliches -Destination (Join-Path $portableStage "cliches.txt") -Force
}
$distRedundancies = Join-Path $repo "dist\redundancies.txt"
if (Test-Path $distRedundancies) {
    Copy-Item -Path $distRedundancies -Destination (Join-Path $portableStage "redundancies.txt") -Force
}
Compress-Archive -Path (Join-Path $portableStage "*") -DestinationPath $portableZip -CompressionLevel Optimal
Remove-Item -Path $portableStage -Recurse -Force

Write-Host "[3/4] Updating installer version to $Version..."
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

Write-Host "[4/4] Building installer (if Inno Setup is installed)..."
$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Warning "Inno Setup (ISCC.exe) not found. EXE and portable ZIP were built, but installer was skipped."
    Write-Host "Install Inno Setup 6 from https://jrsoftware.org/isinfo.php and rerun this script."
    exit 0
}

& $iscc $issPath
Write-Host "Packaging complete. Installer output is in .\\release"
