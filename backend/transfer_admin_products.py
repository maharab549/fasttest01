"""Transfer admin's products to techstore seller"""
from app.database import SessionLocal
from app.models import User, Product

db = SessionLocal()

# Get admin and techstore
admin = db.query(User).filter(User.username == 'admin').first()
techstore = db.query(User).filter(User.username == 'techstore').first()

print(f'\n=== BEFORE TRANSFER ===')
print(f'Admin ID: {admin.id}')
print(f'Techstore ID: {techstore.id}')

# Count products
admin_products = db.query(Product).filter(Product.seller_id == admin.id).all()
techstore_products_before = db.query(Product).filter(Product.seller_id == techstore.id).count()

print(f'\nAdmin products: {len(admin_products)}')
print(f'Techstore products: {techstore_products_before}')

# Transfer all admin products to techstore
print(f'\n=== TRANSFERRING PRODUCTS ===')
for product in admin_products:
    product.seller_id = techstore.id
    print(f'  Transferred: {product.id} - {product.title}')

db.commit()

# Verify
admin_products_after = db.query(Product).filter(Product.seller_id == admin.id).count()
techstore_products_after = db.query(Product).filter(Product.seller_id == techstore.id).count()

print(f'\n=== AFTER TRANSFER ===')
print(f'Admin products: {admin_products_after}')
print(f'Techstore products: {techstore_products_after}')

print(f'\n✅ Successfully transferred {len(admin_products)} products from admin to techstore!')

db.close()
