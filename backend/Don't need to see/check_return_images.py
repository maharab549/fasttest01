from app.database import SessionLocal
from app import models
import json

db = SessionLocal()

returns = db.query(models.Return).all()
print(f'Total returns: {len(returns)}\n')

for r in returns:
    print(f'Return #{r.return_number}:')
    print(f'  Order ID: {r.order_id}')
    print(f'  User ID: {r.user_id}')
    print(f'  Status: {r.status}')
    print(f'  Return Items: {len(r.return_items)}')
    
    for item in r.return_items:
        print(f'\n  Item {item.id}:')
        print(f'    Product ID: {item.product_id}')
        print(f'    Quantity: {item.quantity}')
        print(f'    Reason: {item.reason}')
        print(f'    Condition: {item.condition}')
        print(f'    Images: {item.images}')
        print(f'    Images type: {type(item.images)}')
    print('\n' + '='*50 + '\n')

db.close()
