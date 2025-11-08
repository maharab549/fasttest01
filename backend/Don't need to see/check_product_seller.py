from app.database import SessionLocal
from app.models import User, Product

db = SessionLocal()

# Check product by slug
slug = "dzcxz-6a6add"
product = db.query(Product).filter(Product.slug == slug).first()

if product:
    print(f'\n=== PRODUCT INFO ===')
    print(f'ID: {product.id}')
    print(f'Title: {product.title}')
    print(f'Slug: {product.slug}')
    print(f'Seller ID: {product.seller_id}')
    
    # Get the seller
    seller = db.query(User).filter(User.id == product.seller_id).first()
    if seller:
        print(f'\n=== SELLER INFO ===')
        print(f'Seller ID: {seller.id}')
        print(f'Username: {seller.username}')
        print(f'Email: {seller.email}')
        print(f'Is Admin: {seller.is_admin}')
    else:
        print('\nSeller: NOT FOUND')
else:
    print(f'\nProduct with slug "{slug}": NOT FOUND')

db.close()
