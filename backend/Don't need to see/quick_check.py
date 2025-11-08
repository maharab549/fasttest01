from app.database import SessionLocal
from app.models import User, Product, Return, ReturnItem

db = SessionLocal()

# Get techstore
techstore = db.query(User).filter(User.username == 'techstore').first()
print(f'\n=== TECHSTORE SELLER ===')
print(f'ID: {techstore.id}')
print(f'Username: {techstore.username}')

# Get products
products = db.query(Product).filter(Product.seller_id == techstore.id).all()
print(f'\nProducts sold by techstore: {len(products)}')
for p in products[:10]:
    print(f'  - Product {p.id}: {p.title}')

# Get ALL returns
all_returns = db.query(Return).all()
print(f'\n=== ALL RETURNS ===')
print(f'Total returns in database: {len(all_returns)}')

# Check each return to see which products are being returned
for ret in all_returns:
    print(f'\nReturn {ret.id} ({ret.return_number}):')
    for item in ret.return_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            is_techstore = "✅ TECHSTORE" if product.seller_id == techstore.id else f"Seller ID: {product.seller_id}"
            print(f'  - Product {product.id}: {product.title} [{is_techstore}]')
        else:
            print(f'  - Product {item.product_id}: NOT FOUND')

# Try the exact query from the API
print(f'\n=== API QUERY TEST ===')
api_returns = db.query(Return)\
    .join(ReturnItem)\
    .join(Product, ReturnItem.product_id == Product.id)\
    .filter(Product.seller_id == techstore.id)\
    .distinct()\
    .all()

print(f'Returns found by API query for techstore: {len(api_returns)}')
for ret in api_returns:
    print(f'  - Return {ret.return_number}: Order {ret.order_id}, Status: {ret.status}')

db.close()
