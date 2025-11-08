from app.database import SessionLocal
from app import models

db = SessionLocal()

# Check techstore user
user = db.query(models.User).filter(models.User.username == 'techstore').first()
if not user:
    print("❌ Techstore user not found!")
    db.close()
    exit(1)

print(f"✅ Techstore User:")
print(f"   ID: {user.id}")
print(f"   Username: {user.username}")
print(f"   Is Seller: {user.is_seller}")

# Check seller profile
seller = db.query(models.Seller).filter(models.Seller.user_id == user.id).first()
if not seller:
    print(f"\n❌ No Seller profile found for user_id={user.id}")
else:
    print(f"\n✅ Seller Profile:")
    print(f"   Seller ID: {seller.id}")
    print(f"   User ID: {seller.user_id}")

# Check products by user_id (wrong way)
products_by_user = db.query(models.Product).filter(models.Product.seller_id == user.id).count()
print(f"\n📦 Products with seller_id={user.id} (user.id): {products_by_user}")

# Check products by seller.id (correct way)
if seller:
    products_by_seller = db.query(models.Product).filter(models.Product.seller_id == seller.id).count()
    print(f"📦 Products with seller_id={seller.id} (seller.id): {products_by_seller}")

db.close()
