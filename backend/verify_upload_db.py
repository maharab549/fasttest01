from app.database import SessionLocal
from app import models

db = SessionLocal()

# Check latest ProductImage rows
print("=== Latest ProductImage rows ===")
images = db.query(models.ProductImage).order_by(models.ProductImage.id.desc()).limit(10).all()
for im in images:
    print(f"ID {im.id}: product_id={im.product_id}, image_url={im.image_url}, created_at={im.created_at}")

# Check product 3's images field
print("\n=== Product 3 images field ===")
p = db.query(models.Product).filter(models.Product.id == 3).first()
if p:
    print(f"Product 3 images: {p.images}")
    print(f"Type: {type(p.images)}")
    print(f"Count: {len(p.images) if isinstance(p.images, list) else 'N/A'}")
else:
    print("Product 3 not found!")

db.close()
