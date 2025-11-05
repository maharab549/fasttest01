#!/usr/bin/env python3
"""Check returns in database"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import Return, ReturnItem
from app.database import SessionLocal

# Create session
db = SessionLocal()

try:
    # Get all returns
    returns = db.query(Return).all()
    
    print("\n" + "="*80)
    print(f"TOTAL RETURNS: {len(returns)}")
    print("="*80)
    
    for ret in returns:
        print(f"\nReturn ID: {ret.id}")
        print(f"  Return Number: {ret.return_number}")
        print(f"  Order ID: {ret.order_id}")
        print(f"  User ID: {ret.user_id}")
        print(f"  Status: {ret.status}")
        print(f"  Reason: {ret.reason}")
        print(f"  Created: {ret.created_at}")
        print(f"  Return Items Count: {len(ret.return_items)}")
        
        for item in ret.return_items:
            print(f"    - Item ID: {item.id}")
            print(f"      Order Item ID: {item.order_item_id}")
            print(f"      Product ID: {item.product_id}")
            print(f"      Quantity: {item.quantity}")
            print(f"      Reason: {item.reason}")
        print("-"*80)
    
    print("\n✅ Check complete!\n")
    
finally:
    db.close()
