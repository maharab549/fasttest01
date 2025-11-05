"""
Fix Product seller_id to use Seller.id instead of User.id
"""
from app.database import SessionLocal
from app import models

db = SessionLocal()

print("=== Fixing Product seller_id values ===\n")

# Get all sellers
sellers = db.query(models.Seller).all()
print(f"Found {len(sellers)} sellers\n")

for seller in sellers:
    print(f"Seller ID: {seller.id}, User ID: {seller.user_id}")
    
    # Count products with wrong seller_id (user_id)
    wrong_count = db.query(models.Product).filter(
        models.Product.seller_id == seller.user_id
    ).count()
    
    if wrong_count > 0:
        print(f"  Found {wrong_count} products with seller_id={seller.user_id} (should be {seller.id})")
        
        # Update products
        db.query(models.Product).filter(
            models.Product.seller_id == seller.user_id
        ).update({"seller_id": seller.id})
        
        db.commit()
        print(f"  ✅ Updated {wrong_count} products to seller_id={seller.id}")
    else:
        # Check if they already have correct seller_id
        correct_count = db.query(models.Product).filter(
            models.Product.seller_id == seller.id
        ).count()
        print(f"  Already correct: {correct_count} products with seller_id={seller.id}")
    print()

print("\n=== Verification ===")
for seller in sellers:
    product_count = db.query(models.Product).filter(
        models.Product.seller_id == seller.id
    ).count()
    user = db.query(models.User).filter(models.User.id == seller.user_id).first()
    print(f"Seller '{user.username}' (seller_id={seller.id}): {product_count} products")

db.close()
print("\n✅ Seller IDs fixed!")
