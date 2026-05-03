# Archive selected migration/generator/verify scripts into cleanup_archive\<timestamp>
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$archiveRoot = Join-Path $root "..\..\cleanup_archive\$timestamp"
if (!(Test-Path $archiveRoot)) { New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null }

$files = @(
    'add_product_variant_columns_migration.py',
    'add_stripe_email.py',
    'add_variant_columns.py',
    'create_images_table.py',
    'create_product_variants_table.py',
    'create_table.py',
    'generate_products.py',
    'generate_test_token.py',
    'verify_db.py',
    'verify_upload_db.py'
)

$moved = @()
$missing = @()

foreach ($f in $files) {
    $src = Join-Path $root $f
    if (Test-Path $src) {
        $dest = Join-Path $archiveRoot $f
        $destDir = Split-Path $dest -Parent
        if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
        Move-Item -Path $src -Destination $dest -Force
        $moved += $f
    } else {
        $missing += $f
    }
}

# Append to moved list
$movedListPath = Join-Path $root 'scripts\moved_cleanup_list.txt'
Add-Content -Path $movedListPath -Value "---- $timestamp (migration scripts) ----"
if ($moved.Count -gt 0) { $moved | Out-File -FilePath $movedListPath -Append -Encoding UTF8 }

Write-Output "Archive created: $archiveRoot"
Write-Output "Moved count: $($moved.Count)"
if ($moved.Count -gt 0) { $moved | ForEach-Object { Write-Output " - $_" } }
if ($missing.Count -gt 0) { Write-Output "Missing files:"; $missing | ForEach-Object { Write-Output " - $_" } }
