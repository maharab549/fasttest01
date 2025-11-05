"""
Check product ownership by slug - shows actual seller
"""
from app.database import SessionLocal
from app import models

db = SessionLocal()

slug = "dzcxz-6a6add"

# Get product
product = db.query(models.Product).filter(models.Product.slug == slug).first()

if not product:
    print(f"❌ Product with slug '{slug}' not found")
    db.close()
    exit(1)

print("=== PRODUCT INFO ===")
print(f"ID: {product.id}")
print(f"Title: {product.title}")
print(f"Slug: {product.slug}")
print(f"Product.seller_id: {product.seller_id}")

# Get seller profile
seller = db.query(models.Seller).filter(models.Seller.id == product.seller_id).first()

if seller:
    print("\n=== SELLER PROFILE ===")
    print(f"Seller ID: {seller.id}")
    print(f"Seller User ID: {seller.user_id}")
    
    # Get the user
    user = db.query(models.User).filter(models.User.id == seller.user_id).first()
    if user:
        print(f"\n=== SELLER USER ===")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Is Seller: {user.is_seller}")
        print(f"Is Admin: {user.is_admin}")
else:
    print("\n❌ No seller profile found!")

db.close()
