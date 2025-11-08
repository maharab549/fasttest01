#!/usr/bin/env python3
"""
Generate missing placeholder images for products.
This script creates PNG files for all products that are referenced in the database
but are missing from disk.
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app import models

def create_placeholder_image(product_name, filename, size=(400, 400)):
    """Create a placeholder image for a product."""
    try:
        # Create image with gradient background
        img = Image.new('RGB', size, color=(100, 120, 200))
        draw = ImageDraw.Draw(img)
        
        # Try to use a nicer font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", 24)
            small_font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw placeholder symbol (just a rectangle with text)
        margin = 20
        draw.rectangle([margin, margin, size[0]-margin, size[1]-margin], 
                      outline=(255, 255, 255), width=3)
        
        # Center text
        text_y = size[1] // 2 - 40
        text = product_name[:30]  # Truncate if too long
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = (size[0] - text_width) // 2
        
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
        
        # Add "Product Image" label at bottom
        label = "Product Image"
        bbox = draw.textbbox((0, 0), label, font=small_font)
        label_width = bbox[2] - bbox[0]
        label_x = (size[0] - label_width) // 2
        draw.text((label_x, size[1] - 60), label, fill=(200, 200, 255), font=small_font)
        
        # Save image
        img.save(filename)
        return True
    except Exception as e:
        print(f"Error creating image {filename}: {e}", file=sys.stderr)
        return False

def main():
    """Generate missing product images."""
    db = SessionLocal()
    
    # Ensure uploads directory exists
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'products')
    os.makedirs(uploads_dir, exist_ok=True)
    
    print(f"Images directory: {uploads_dir}")
    print()
    
    # Get all products
    products = db.query(models.Product).all()
    print(f"Total products in database: {len(products)}")
    
    created = 0
    already_exist = 0
    failed = 0
    
    for product in products:
        if not product.images:
            continue
            
        # Extract first image path from product.images JSON
        try:
            if isinstance(product.images, list):
                images_list = product.images
            elif isinstance(product.images, str):
                images_list = json.loads(product.images)
            else:
                continue
        except:
            continue
        
        if not images_list or not isinstance(images_list, list):
            continue
        
        first_image = images_list[0]
        if not isinstance(first_image, str):
            continue
        
        # Extract filename from path (handle both /uploads/products/X.png and X.png)
        if '/' in first_image:
            filename = first_image.split('/')[-1]
        else:
            filename = first_image
        
        filepath = os.path.join(uploads_dir, filename)
        
        # Check if file exists
        if os.path.exists(filepath):
            already_exist += 1
            continue
        
        # Create placeholder
        product_name = getattr(product, 'title', None) or getattr(product, 'name', None) or f"Product {product.id}"
        if create_placeholder_image(product_name, filepath):
            created += 1
            print(f"✓ Created: {filename}")
        else:
            failed += 1
            print(f"✗ Failed: {filename}")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Images created:    {created}")
    print(f"Already existed:   {already_exist}")
    print(f"Failed:            {failed}")
    print(f"Total processed:   {created + already_exist + failed}")
    print()
    
    # Also check ProductImage entries
    print("=" * 60)
    print("Checking ProductImage table...")
    print("=" * 60)
    
    product_images = db.query(models.ProductImage).all()
    print(f"Total ProductImage rows: {len(product_images)}")
    
    pi_created = 0
    pi_exist = 0
    pi_failed = 0
    
    for pi in product_images:
        if not pi.image_url:
            continue
        
        # Extract filename
        if '/' in pi.image_url:
            filename = pi.image_url.split('/')[-1]
        else:
            filename = pi.image_url
        
        filepath = os.path.join(uploads_dir, filename)
        
        if os.path.exists(filepath):
            pi_exist += 1
            continue
        
        # Create placeholder with a generic name
        product_name = f"Image {pi.id}"
        if create_placeholder_image(product_name, filepath):
            pi_created += 1
            print(f"✓ Created: {filename}")
        else:
            pi_failed += 1
            print(f"✗ Failed: {filename}")
    
    print()
    print("ProductImage results:")
    print(f"  Created:    {pi_created}")
    print(f"  Existed:    {pi_exist}")
    print(f"  Failed:     {pi_failed}")
    
    db.close()
    
    total_created = created + pi_created
    print()
    print(f"Total new images created: {total_created}")
    if total_created > 0:
        print("✓ All missing images have been generated!")
        print("\nNext steps:")
        print("1. Hard refresh the browser (Ctrl+Shift+R)")
        print("2. Check if product images now display correctly")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
