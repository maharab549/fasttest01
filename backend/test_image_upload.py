"""Test image upload functionality"""
import os
import sys
import shutil
sys.path.insert(0, '.')

from app.database import SessionLocal, engine, Base
from app import models, crud

# Create all tables
Base.metadata.create_all(bind=engine)

# Get a database session
db = SessionLocal()

try:
    # First, find a product to upload an image for
    product = db.query(models.Product).first()
    
    if not product:
        print("No products found in database")
        sys.exit(1)
    
    print(f"Found product: {product.id} - {product.name}")
    print(f"Current images in product.images: {product.images}")
    
    # Check how many images are currently in the ProductImage table
    image_count = db.query(models.ProductImage).filter(
        models.ProductImage.product_id == product.id
    ).count()
    print(f"Current ProductImages in DB for this product: {image_count}")
    
    # Try to create a test image
    print("\nAttempting to create a test ProductImage...")
    test_image = crud.create_product_image(
        db=db,
        product_id=product.id,
        image_url="/uploads/products/test_image.jpg",
        alt_text="Test image"
    )
    
    print(f"SUCCESS! Created ProductImage:")
    print(f"  ID: {test_image.id}")
    print(f"  Product ID: {test_image.product_id}")
    print(f"  Image URL: {test_image.image_url}")
    print(f"  Alt Text: {test_image.alt_text}")
    print(f"  Created At: {test_image.created_at}")
    
    # Verify it was actually saved to DB
    db.refresh(db)
    image_count_after = db.query(models.ProductImage).filter(
        models.ProductImage.product_id == product.id
    ).count()
    print(f"\nProductImages in DB after create: {image_count_after}")
    
    # Query the image directly to confirm
    direct_query = db.query(models.ProductImage).filter(
        models.ProductImage.id == test_image.id
    ).first()
    
    if direct_query:
        print("CONFIRMED: Image found in database on direct query")
    else:
        print("ERROR: Image NOT found in database on direct query")
    
    print("\nTest completed successfully!")
    
finally:
    db.close()
