"""
Code Quality Cleanup Script
Removes duplicate, backup, and old files
"""
import os
import shutil
from pathlib import Path

def find_duplicate_files(root_dir):
    """Find files with .backup, .old, _old, _backup extensions or similar"""
    patterns = [
        "*.backup",
        "*.old",
        "*_old.*",
        "*_backup.*",
        "*.bak",
        "*_copy.*",
        "*.tmp",
        "*~",
    ]
    
    duplicate_files = []
    
    for pattern in patterns:
        for file_path in Path(root_dir).rglob(pattern):
            if file_path.is_file():
                duplicate_files.append(file_path)
    
    return duplicate_files

def find_pycache_dirs(root_dir):
    """Find all __pycache__ directories"""
    pycache_dirs = []
    for dirpath, dirnames, _ in os.walk(root_dir):
        if '__pycache__' in dirnames:
            pycache_dirs.append(os.path.join(dirpath, '__pycache__'))
    return pycache_dirs

def cleanup_files(root_dir, dry_run=True):
    """
    Clean up duplicate and cache files
    
    Args:
        root_dir: Root directory to search
        dry_run: If True, only list files without deleting
    """
    print(f"Scanning {root_dir} for duplicate and cache files...")
    print("="*60)
    
    # Find duplicate files
    duplicate_files = find_duplicate_files(root_dir)
    
    # Find __pycache__ directories
    pycache_dirs = find_pycache_dirs(root_dir)
    
    print(f"\nFound {len(duplicate_files)} duplicate/backup files:")
    total_size = 0
    for file_path in duplicate_files:
        size = file_path.stat().st_size
        total_size += size
        print(f"  - {file_path} ({size / 1024:.2f} KB)")
    
    print(f"\nFound {len(pycache_dirs)} __pycache__ directories:")
    for dir_path in pycache_dirs:
        print(f"  - {dir_path}")
    
    print(f"\nTotal space to be freed: {total_size / 1024 / 1024:.2f} MB")
    
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN - No files were deleted")
        print("Run with dry_run=False to actually delete files")
        return
    
    # Delete duplicate files
    deleted_count = 0
    for file_path in duplicate_files:
        try:
            file_path.unlink()
            deleted_count += 1
            print(f"Deleted: {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
    
    # Delete __pycache__ directories
    for dir_path in pycache_dirs:
        try:
            shutil.rmtree(dir_path)
            print(f"Deleted: {dir_path}")
        except Exception as e:
            print(f"Error deleting {dir_path}: {e}")
    
    print("\n" + "="*60)
    print(f"Cleanup complete! Deleted {deleted_count} files and {len(pycache_dirs)} directories")
    print(f"Freed {total_size / 1024 / 1024:.2f} MB of space")

if __name__ == "__main__":
    import sys
    
    # Get backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if user wants to actually delete files
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        dry_run = False
        print("WARNING: This will permanently delete files!")
        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            sys.exit(0)
    
    cleanup_files(backend_dir, dry_run=dry_run)
