#!/usr/bin/env python3
"""
Scan and repair legacy image paths in the database.

Converts relative paths (products/..., uploads/..., etc.) to absolute /uploads/... paths.
Also optionally verifies that files exist on disk.

Usage:
  python scripts/repair_image_paths.py [--check-files] [--fix]
  
  --check-files: Verify each image file exists under backend/uploads/products/
  --fix:         Actually update the database (default is dry-run)
"""
import json
import os
import sys
from pathlib import Path

# Ensure app module is importable
sys.path.insert(0, os.getcwd())

from app.database import SessionLocal
from app import models


def normalize_path(path_str):
    """Normalize a relative/absolute image path to /uploads/... format."""
    if not path_str:
        return None
    
    s = str(path_str).strip()
    
    # Already correct
    if s.startswith('/uploads/products/'):
        return s
    if s.startswith('/uploads/'):
        return s
    
    # Common relative formats
    if s.startswith('uploads/products/'):
        return '/' + s
    if s.startswith('uploads/'):
        return '/' + s
    if s.startswith('products/'):
        return '/uploads/' + s
    if s.startswith('./products/'):
        return '/uploads/products/' + s[11:]
    if s.startswith('./uploads/'):
        return '/' + s[2:]
    
    # Absolute URLs (leave as-is)
    if s.startswith('http://') or s.startswith('https://'):
        return s
    
    # Unknown format: prepend /uploads/
    return '/uploads/' + s


def check_file_exists(normalized_path):
    """Check if the file exists on disk."""
    if not normalized_path or normalized_path.startswith('http'):
        return None  # Can't check remote URLs
    
    # Map /uploads/... to backend/uploads/...
    file_path = Path('uploads') / normalized_path.lstrip('/')
    return file_path.exists()


def scan_products(session, check_files=False):
    """Scan Product.images JSON field for legacy paths."""
    print("\n=== Scanning Product Images ===")
    
    products_scanned = 0
    paths_found = {}
    broken_files = []
    
    products = session.query(models.Product).filter(models.Product.images != None).all()
    
    for product in products:
        products_scanned += 1
        raw_images = product.images
        
        if isinstance(raw_images, list):
            for img in raw_images:
                img_str = str(img)
                if img_str not in paths_found:
                    paths_found[img_str] = {'count': 0, 'normalized': normalize_path(img_str), 'product_ids': []}
                paths_found[img_str]['count'] += 1
                paths_found[img_str]['product_ids'].append(product.id)
                
                if check_files:
                    normalized = paths_found[img_str]['normalized']
                    if not check_file_exists(normalized):
                        broken_files.append({
                            'product_id': product.id,
                            'slug': product.slug,
                            'original': img_str,
                            'normalized': normalized
                        })
    
    print(f"Products scanned: {products_scanned}")
    print(f"Unique image paths found: {len(paths_found)}")
    
    legacy_paths = [p for p in paths_found if normalize_path(p) != p]
    print(f"Legacy/broken paths: {len(legacy_paths)}")
    
    if legacy_paths:
        print("\nLegacy paths detected:")
        for path in sorted(legacy_paths)[:20]:  # Show first 20
            normalized = normalize_path(path)
            count = paths_found[path]['count']
            print(f"  {path} -> {normalized} ({count} occurrences)")
    
    if check_files and broken_files:
        print(f"\nBroken files (not found on disk): {len(broken_files)}")
        for item in broken_files[:10]:
            print(f"  Product {item['product_id']} ({item['slug']}): {item['normalized']}")
    
    return paths_found, broken_files


def scan_product_images(session, check_files=False):
    """Scan ProductImage.image_url field for legacy paths."""
    print("\n=== Scanning ProductImage URLs ===")
    
    images_scanned = 0
    paths_found = {}
    broken_files = []
    
    product_images = session.query(models.ProductImage).all()
    
    for img in product_images:
        images_scanned += 1
        url = str(img.image_url) if img.image_url else ''
        
        if url and url not in paths_found:
            paths_found[url] = {'count': 0, 'normalized': normalize_path(url), 'image_ids': []}
        
        if url:
            paths_found[url]['count'] += 1
            paths_found[url]['image_ids'].append(img.id)
            
            if check_files:
                normalized = paths_found[url]['normalized']
                if not check_file_exists(normalized):
                    broken_files.append({
                        'image_id': img.id,
                        'product_id': img.product_id,
                        'original': url,
                        'normalized': normalized
                    })
    
    print(f"ProductImage rows scanned: {images_scanned}")
    print(f"Unique URLs found: {len(paths_found)}")
    
    legacy_paths = [p for p in paths_found if normalize_path(p) != p]
    print(f"Legacy/broken paths: {len(legacy_paths)}")
    
    if legacy_paths:
        print("\nLegacy paths detected:")
        for path in sorted(legacy_paths)[:20]:
            normalized = normalize_path(path)
            count = paths_found[path]['count']
            print(f"  {path} -> {normalized} ({count} occurrences)")
    
    if check_files and broken_files:
        print(f"\nBroken files (not found on disk): {len(broken_files)}")
        for item in broken_files[:10]:
            print(f"  ProductImage {item['image_id']}: {item['normalized']}")
    
    return paths_found, broken_files


def repair_products(session, fix=False):
    """Repair Product.images JSON paths."""
    print("\n=== Repairing Product Images ===")
    
    products_to_fix = session.query(models.Product).filter(models.Product.images != None).all()
    fixed_count = 0
    rows_fixed = []
    
    for product in products_to_fix:
        raw_images = product.images
        if not isinstance(raw_images, list):
            continue
        
        normalized = [normalize_path(str(img)) for img in raw_images]
        if normalized != raw_images:
            rows_fixed.append({
                'product_id': product.id,
                'slug': product.slug,
                'before': raw_images,
                'after': normalized
            })
            fixed_count += 1
            
            if fix:
                product.images = normalized
    
    if fixed_count > 0:
        print(f"Products needing repair: {fixed_count}")
        if fix:
            session.commit()
            print("✓ FIXED in database")
        else:
            print("(dry-run: no changes made)")
        
        if rows_fixed:
            print(f"\nFirst product fix:")
            sample = rows_fixed[0]
            print(f"  Product {sample['product_id']} ({sample['slug']})")
            print(f"    Before: {sample['before']}")
            print(f"    After:  {sample['after']}")
    else:
        print("No products need repair.")
    
    return fixed_count


def repair_product_images(session, fix=False):
    """Repair ProductImage.image_url paths."""
    print("\n=== Repairing ProductImage URLs ===")
    
    product_images = session.query(models.ProductImage).all()
    fixed_count = 0
    rows_fixed = []
    
    for img in product_images:
        url = str(img.image_url) if img.image_url else ''
        if not url:
            continue
        
        normalized = normalize_path(url)
        if normalized != url:
            rows_fixed.append({
                'image_id': img.id,
                'product_id': img.product_id,
                'before': url,
                'after': normalized
            })
            fixed_count += 1
            
            if fix:
                img.image_url = normalized
    
    if fixed_count > 0:
        print(f"ProductImage rows needing repair: {fixed_count}")
        if fix:
            session.commit()
            print("✓ FIXED in database")
        else:
            print("(dry-run: no changes made)")
        
        if rows_fixed:
            print(f"\nFirst image fix:")
            sample = rows_fixed[0]
            print(f"  ProductImage {sample['image_id']} (product {sample['product_id']})")
            print(f"    Before: {sample['before']}")
            print(f"    After:  {sample['after']}")
    else:
        print("No ProductImage rows need repair.")
    
    return fixed_count


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scan and repair legacy image paths in the database.'
    )
    parser.add_argument('--check-files', action='store_true', help='Verify files exist on disk')
    parser.add_argument('--fix', action='store_true', help='Actually update the database (default: dry-run)')
    
    args = parser.parse_args()
    
    session = SessionLocal()
    
    try:
        print("=" * 60)
        print("IMAGE PATH REPAIR UTILITY")
        print("=" * 60)
        print(f"Mode: {'DRY-RUN' if not args.fix else 'FIX MODE (updating database)'}")
        print(f"File check: {'enabled' if args.check_files else 'disabled'}")
        
        # Scan phase
        prod_paths, prod_broken = scan_products(session, check_files=args.check_files)
        img_paths, img_broken = scan_product_images(session, check_files=args.check_files)
        
        # Repair phase
        prod_fixed = repair_products(session, fix=args.fix)
        img_fixed = repair_product_images(session, fix=args.fix)
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total fixes needed:")
        print(f"  Product images: {prod_fixed}")
        print(f"  ProductImage rows: {img_fixed}")
        print(f"  Total: {prod_fixed + img_fixed}")
        
        if args.check_files:
            broken_total = len(prod_broken) + len(img_broken)
            if broken_total > 0:
                print(f"\nBroken files (not found): {broken_total}")
                print(f"  Consider uploading missing images to backend/uploads/products/")
        
        if not args.fix and (prod_fixed + img_fixed) > 0:
            print(f"\nTo apply fixes, run with --fix flag:")
            print(f"  python scripts/repair_image_paths.py --fix")
        
    finally:
        session.close()


if __name__ == '__main__':
    main()
