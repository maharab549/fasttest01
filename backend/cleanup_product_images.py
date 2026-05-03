from app.database import SessionLocal
from app import models

db = SessionLocal()

print("=== DB Cleanup: Removing non-numeric entries from product.images ===\n")

# Get all products
products = db.query(models.Product).all()
cleaned_count = 0
total_products = len(products)

for product in products:
    if not product.images:
        continue
    
    if not isinstance(product.images, list):
        print(f"Product {product.id}: images is not a list (type={type(product.images)}), skipping")
        continue
    
    # Filter to numeric IDs only
    original_images = product.images.copy()
    cleaned_images = []
    
    for image in original_images:
        try:
            # Try to convert to int
            image_id = int(image)
            cleaned_images.append(image_id)
        except (ValueError, TypeError):
            # Non-numeric entry (e.g., data URI, string)
            print(f"Product {product.id}: Removing non-numeric entry: {str(image)[:80]}...")
            cleaned_count += 1
    
    # Update if changed
    if len(cleaned_images) != len(original_images):
        product.images = cleaned_images
        db.commit()
        print(f"Product {product.id}: Updated images from {len(original_images)} to {len(cleaned_images)} entries")

print(f"\n=== Summary ===")
print(f"Total products: {total_products}")
print(f"Total non-numeric entries removed: {cleaned_count}")
print(f"DB commit completed.")

db.close()
