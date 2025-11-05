from app.database import SessionLocal
from app.models import User, Product

db = SessionLocal()

# Check seller ID 1
seller = db.query(User).filter(User.id == 1).first()
print(f'Seller ID 1: {seller.username if seller else "NOT FOUND"}')

# Check product 1583
product = db.query(Product).filter(Product.id == 1583).first()
if product:
    print(f'\nProduct 1583: {product.title}')
    print(f'Seller ID: {product.seller_id}')
    
    # Get the seller
    seller = db.query(User).filter(User.id == product.seller_id).first()
    if seller:
        print(f'Seller: {seller.username}')
else:
    print('\nProduct 1583: NOT FOUND')

db.close()
