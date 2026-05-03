# Second-pass cleanup to move test_*.py, tmp_*.py and front/frontend/dist into cleanup_archive/<timestamp>
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$archiveRoot = Join-Path $root "..\..\cleanup_archive\$timestamp"
if (!(Test-Path $archiveRoot)) { New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null }

$moved = @()

# Move test_*.py and tmp_*.py anywhere under repo, excluding venv and existing archive
$files = Get-ChildItem -Path $root -Recurse -Include "test_*.py","tmp_*.py" -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\venv\\" -and $_.FullName -notmatch "\\cleanup_archive\\" }
foreach ($f in $files) {
    $rel = $f.FullName.Substring($root.Length + 1)
    $dest = Join-Path $archiveRoot $rel
    $destDir = Split-Path $dest -Parent
    if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    try {
        Move-Item -Path $f.FullName -Destination $dest -Force
        $moved += $rel
    } catch {
        Write-Warning "Failed to move $($f.FullName): $_"
    }
}

# Move front/frontend/dist if present
$distPath = Join-Path $root "..\..\front\frontend\dist"
if (Test-Path $distPath) {
    $rel = (Get-Item $distPath).FullName.Substring($root.Length + 1)
    $dest = Join-Path $archiveRoot $rel
    $destDir = Split-Path $dest -Parent
    if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    try {
    Move-Item -Path $distPath -Destination $dest -Force
        $moved += $rel
    } catch {
        Write-Warning ('Failed to move ' + $distPath + ': ' + $_)
    }
}

# Append moved list to scripts/moved_cleanup_list.txt
$movedListPath = Join-Path $root "scripts\moved_cleanup_list.txt"
if (!(Test-Path (Split-Path $movedListPath -Parent))) { New-Item -ItemType Directory -Path (Split-Path $movedListPath -Parent) -Force | Out-Null }
if ($moved.Count -gt 0) {
    Add-Content -Path $movedListPath -Value "---- $timestamp ----"
    $moved | Out-File -FilePath $movedListPath -Encoding UTF8 -Append
}

Write-Output "Second pass archive complete: $archiveRoot"
Write-Output "Moved items (count): $($moved.Count)"
if ($moved.Count -gt 0) { $moved | Select-Object -First 50 | ForEach-Object { Write-Output " - $_" } }
