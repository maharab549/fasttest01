#!/usr/bin/env python
"""Check the current status of product images in the database"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models import ProductImage, Product
import json

db = SessionLocal()

try:
    # Check total product images
    total_images = db.query(ProductImage).count()
    print(f"\n✅ Total ProductImages in database: {total_images}")
    
    if total_images > 0:
        # Show first 5 images
        images = db.query(ProductImage).limit(5).all()
        print(f"\nFirst {min(5, total_images)} images:")
        for img in images:
            print(f"  - ID: {img.id}, Product: {img.product_id}, URL: {img.image_url}")
    
    # Check products with images
    products_with_images = db.query(Product).filter(Product.images != None).filter(Product.images != "[]").count()
    print(f"\n✅ Products with images array: {products_with_images}")
    
    # Show sample products
    sample_products = db.query(Product).filter(Product.images != None).filter(Product.images != "[]").limit(3).all()
    if sample_products:
        print(f"\nSample products with images:")
        for p in sample_products:
            images_list = json.loads(p.images) if isinstance(p.images, str) else p.images or []
            print(f"  - Product {p.id}: {p.title} - {len(images_list)} images")
            
finally:
    db.close()
    print("\n✅ Database check complete!")
