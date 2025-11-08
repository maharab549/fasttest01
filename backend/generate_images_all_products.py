#!/usr/bin/env python3
"""
Generate and assign images to ALL products that don't have any.
Creates placeholder images for each product and adds them to the database.
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
        img.save(filename)
        return True
    except Exception as e:
        print(f"Error creating {filename}: {e}", file=sys.stderr)
        return False

def main():
    db = SessionLocal()
    
    # Ensure uploads directory exists
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'products')
    os.makedirs(uploads_dir, exist_ok=True)
    
    print(f"Images directory: {uploads_dir}")
    print()
    
    # Get all products
    all_products = db.query(models.Product).all()
    print(f"Total products: {len(all_products)}")
    
    # Filter products without images
    products_without_images = []
    for p in all_products:
        if not p.images:
            products_without_images.append(p)
        else:
            try:
                if isinstance(p.images, str):
                    images_list = json.loads(p.images)
                else:
                    images_list = p.images
                if not images_list or len(images_list) == 0:
                    products_without_images.append(p)
            except:
                products_without_images.append(p)
    
    print(f"Products without images: {len(products_without_images)}")
    print(f"Products with images: {len(all_products) - len(products_without_images)}")
    print()
    print("Generating images and updating database...")
    print()
    
    created = 0
    failed = 0
    
    for i, product in enumerate(products_without_images, 1):
        # Create image filename
        image_filename = f"product_{product.id}.png"
        image_path = os.path.join(uploads_dir, image_filename)
        
        # Create placeholder image
        product_title = getattr(product, 'title', None) or f"Product {product.id}"
        if create_placeholder_image(product.id, product_title, image_path):
            # Update product with image URL
            image_url = f"/uploads/products/{image_filename}"
            product.images = [image_url]
            db.add(product)
            created += 1
            
            if i % 50 == 0:
                print(f"  [{i}/{len(products_without_images)}] Created {i} images...")
                db.commit()
        else:
            failed += 1
    
    # Final commit
    db.commit()
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Images created:     {created}")
    print(f"Failed:             {failed}")
    print(f"Total processed:    {created + failed}")
    print()
    
    # Verify
    updated_products = db.query(models.Product).all()
    with_images = [p for p in updated_products if p.images and (isinstance(p.images, list) and len(p.images) > 0)]
    without_images = [p for p in updated_products if not p.images or (isinstance(p.images, list) and len(p.images) == 0)]
    
    print("Verification:")
    print(f"  Total products:          {len(updated_products)}")
    print(f"  Products with images:    {len(with_images)}")
    print(f"  Products without images: {len(without_images)}")
    print(f"  Coverage:                {len(with_images)*100/len(updated_products):.1f}%")
    print()
    
    if created > 0:
        print("✓ All products now have images!")
        print("\nNext steps:")
        print("1. Hard refresh the browser (Ctrl+Shift+R)")
        print("2. View product pages to see the new images")
    
    db.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
