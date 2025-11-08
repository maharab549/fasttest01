#!/usr/bin/env python3
"""
Fix image mismatch: sync database image references with actual files on disk.
Creates missing image files for all products with database entries.
"""

import os
import sys
import json
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app import models

def create_placeholder_image(product_id, product_title, filename, size=(400, 400)):
    """Create a placeholder image for a product."""
    try:
        # Create image with gradient background
        img = Image.new('RGB', size, color=(100, 150, 220))
        draw = ImageDraw.Draw(img)
        
        # Try to use a nicer font
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            small_font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw border
        margin = 15
        draw.rectangle([margin, margin, size[0]-margin, size[1]-margin], 
                      outline=(255, 255, 255), width=2)
        
        # Draw product title
        text = product_title[:35] if product_title else f"Product #{product_id}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = (size[0] - text_width) // 2
        draw.text((text_x, 80), text, fill=(255, 255, 255), font=font)
        
        # Draw ID
        id_text = f"ID: {product_id}"
        bbox = draw.textbbox((0, 0), id_text, font=small_font)
        id_width = bbox[2] - bbox[0]
        id_x = (size[0] - id_width) // 2
        draw.text((id_x, 160), id_text, fill=(200, 200, 255), font=small_font)
        
        # Draw product image label
        label = "Product Image"
        bbox = draw.textbbox((0, 0), label, font=small_font)
        label_width = bbox[2] - bbox[0]
        label_x = (size[0] - label_width) // 2
        draw.text((label_x, size[1] - 50), label, fill=(200, 220, 255), font=small_font)
        
        # Save image
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        img.save(filename)
        return True
    except Exception as e:
        print(f"✗ Error: {filename}: {e}", file=sys.stderr)
        return False

def main():
    db = SessionLocal()
    
    # Ensure uploads directory exists
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'products')
    os.makedirs(uploads_dir, exist_ok=True)
    
    print(f"Images directory: {uploads_dir}")
    print()
    
    # Count files on disk
    existing_files = set()
    if os.path.exists(uploads_dir):
        existing_files = set(os.listdir(uploads_dir))
    
    print(f"Files on disk: {len(existing_files)}")
    print()
    
    # Get all products with images in database
    all_products = db.query(models.Product).all()
    products_with_db_images = []
    
    for p in all_products:
        try:
            if isinstance(p.images, str):
                images_list = json.loads(p.images)
            else:
                images_list = p.images
            
            if images_list and len(images_list) > 0:
                products_with_db_images.append((p, images_list))
        except:
            pass
    
    print(f"Products in database with image references: {len(products_with_db_images)}")
    print()
    print("Generating missing image files...")
    print()
    
    created = 0
    already_exist = 0
    failed = 0
    
    for i, (product, images_list) in enumerate(products_with_db_images, 1):
        first_image_url = images_list[0] if images_list else None
        if not first_image_url or not isinstance(first_image_url, str):
            continue
        
        # Extract filename from URL
        if '/' in first_image_url:
            filename = first_image_url.split('/')[-1]
        else:
            filename = first_image_url
        
        filepath = os.path.join(uploads_dir, filename)
        
        # Check if file already exists
        if os.path.exists(filepath):
            already_exist += 1
        else:
            # Create image
            product_title = getattr(product, 'title', None) or f"Product {product.id}"
            if create_placeholder_image(product.id, product_title, filepath):
                created += 1
                if i % 100 == 0:
                    print(f"  [{i}/{len(products_with_db_images)}] Progress...")
            else:
                failed += 1
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files created:      {created}")
    print(f"Files existed:      {already_exist}")
    print(f"Failed:             {failed}")
    print(f"Total processed:    {created + already_exist + failed}")
    print()
    
    # Count files on disk after generation
    new_file_count = len(os.listdir(uploads_dir)) if os.path.exists(uploads_dir) else 0
    print(f"Files on disk now:  {new_file_count}")
    print()
    
    if created > 0:
        print("✓ Missing image files have been generated!")
        print("\nNext steps:")
        print("1. Hard refresh the browser (Ctrl+Shift+R)")
        print("2. View product pages to see the images")
    
    db.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
