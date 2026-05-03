# Archive markdown files, check_*.py (outside scripts), and remaining test_*.py
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$archiveRoot = Join-Path $root "..\..\cleanup_archive\$timestamp"
if (!(Test-Path $archiveRoot)) { New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null }

$moved = @()

# 1) Move .md files (exclude venv and archive)
$mdFiles = Get-ChildItem -Path $root -Recurse -Include "*.md" -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\venv\\" -and $_.FullName -notmatch "\\cleanup_archive\\" }
foreach ($f in $mdFiles) {
    $rel = $f.FullName.Substring($root.Length + 1)
    $dest = Join-Path $archiveRoot $rel
    $destDir = Split-Path $dest -Parent
    if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    try {
        Move-Item -Path $f.FullName -Destination $dest -Force
        $moved += $rel
    } catch {
        Write-Warning ('Failed to move ' + $f.FullName + ': ' + $_)
    }
}

# 2) Move check_*.py files outside scripts/ and venv/
$checkFiles = Get-ChildItem -Path $root -Recurse -Include "check_*.py" -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\venv\\" -and $_.FullName -notmatch "\\cleanup_archive\\" -and $_.FullName -notmatch "\\scripts\\" }
foreach ($f in $checkFiles) {
    $rel = $f.FullName.Substring($root.Length + 1)
    $dest = Join-Path $archiveRoot $rel
    $destDir = Split-Path $dest -Parent
    if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    try {
        Move-Item -Path $f.FullName -Destination $dest -Force
        $moved += $rel
    } catch {
        Write-Warning ('Failed to move ' + $f.FullName + ': ' + $_)
    }
}

# 3) Move remaining test_*.py files that are still present (outside venv and archive)
$testFiles = Get-ChildItem -Path $root -Recurse -Include "test_*.py" -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\venv\\" -and $_.FullName -notmatch "\\cleanup_archive\\" }
foreach ($f in $testFiles) {
    $rel = $f.FullName.Substring($root.Length + 1)
    $dest = Join-Path $archiveRoot $rel
    $destDir = Split-Path $dest -Parent
    if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    try {
        Move-Item -Path $f.FullName -Destination $dest -Force
        $moved += $rel
    } catch {
        Write-Warning ('Failed to move ' + $f.FullName + ': ' + $_)
    }
}

# Append moved list to scripts/moved_cleanup_list.txt
$movedListPath = Join-Path $root "scripts\moved_cleanup_list.txt"
if (!(Test-Path (Split-Path $movedListPath -Parent))) { New-Item -ItemType Directory -Path (Split-Path $movedListPath -Parent) -Force | Out-Null }
if ($moved.Count -gt 0) {
    Add-Content -Path $movedListPath -Value "---- $timestamp ----"
    $moved | Out-File -FilePath $movedListPath -Encoding UTF8 -Append
}

Write-Output "Archive complete: $archiveRoot"
Write-Output "Moved items count: $($moved.Count)"
if ($moved.Count -gt 0) { $moved | Select-Object -First 200 | ForEach-Object { Write-Output " - $_" } }
