# Cleanup and archive dev/test files into cleanup_archive\<timestamp>
# - Moves: fasttest01/backend/test_*.py, fasttest01/backend/tmp_*.py, fasttest01/backend/tests/, front/frontend/dist/
# - Moves non-venv __pycache__ directories
# - Writes moved file list to scripts/moved_cleanup_list.txt

$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$archiveRoot = Join-Path $root "..\..\cleanup_archive\$timestamp"
# archiveRoot resolves to repository root/cleanup_archive/<timestamp>
if (!(Test-Path $archiveRoot)) { New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null }

$movedList = @()

# Patterns to move (relative to repository root)
$patterns = @(
    "fasttest01\backend\test_*.py",
    "fasttest01\backend\tmp_*.py",
    "fasttest01\backend\tests",
    "front\frontend\dist"
)

foreach ($p in $patterns) {
    Write-Output "Processing pattern: $p"
    # If this points at a directory, Get-ChildItem will list its contents; include the directory itself when present
    $items = Get-ChildItem -Path (Join-Path $root $p) -Force -Recurse -ErrorAction SilentlyContinue | ForEach-Object { $_ } 
    # Also include directory node if it exists
    if (Test-Path (Join-Path $root $p) -PathType Container) {
        $items = @((Get-Item -Path (Join-Path $root $p))) + $items
    }

    foreach ($it in $items) {
        $full = $it.FullName
        if ($full -match "\\venv\\") { continue }
        if ($full -match "\\cleanup_archive\\") { continue }
        # compute relative path to root
        $rel = $full.Substring($root.Length + 1)
        $dest = Join-Path $archiveRoot $rel
        $destDir = Split-Path $dest -Parent
        if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
        try {
            Move-Item -Path $full -Destination $dest -Force
            $movedList += $rel
        } catch {
            Write-Warning "Failed to move $full : $_"
        }
    }
}

# Move non-venv __pycache__ directories across repo (excluding venv and archive)
$pycaches = Get-ChildItem -Path $root -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\venv\\" -and $_.FullName -notmatch "\\cleanup_archive\\" }
foreach ($dir in $pycaches) {
    $full = $dir.FullName
    $rel = $full.Substring($root.Length + 1)
    $dest = Join-Path $archiveRoot $rel
    $destDir = Split-Path $dest -Parent
    if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    try {
        Move-Item -Path $full -Destination $dest -Force
        $movedList += $rel
    } catch {
        Write-Warning "Failed to move $full : $_"
    }
}

# Write moved list and summary
$movedListPath = Join-Path $root "scripts\moved_cleanup_list.txt"
if (!(Test-Path (Split-Path $movedListPath -Parent))) { New-Item -ItemType Directory -Path (Split-Path $movedListPath -Parent) -Force | Out-Null }
$movedList | Out-File -FilePath $movedListPath -Encoding UTF8

Write-Output "Archive complete: $archiveRoot"
Write-Output "Moved items count: $($movedList.Count)"
Write-Output "Moved list saved to: $movedListPath"

# Print a few moved items for quick inspection
if ($movedList.Count -gt 0) {
    $movedList | Select-Object -First 20 | ForEach-Object { Write-Output " - $_" }
}
