#!/usr/bin/env python3
"""Debug seller returns - check what's in the database"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import Return, ReturnItem, Product, User, OrderItem, Order
from app.database import SessionLocal

# Create session
db = SessionLocal()

try:
    print("\n" + "="*80)
    print("SELLER RETURNS DEBUG")
    print("="*80)
    
    # Get all returns with their items and products
    returns = db.query(Return).all()
    
    print(f"\nTotal Returns in DB: {len(returns)}")
    
    for ret in returns:
        print(f"\n--- Return #{ret.id} (Order: {ret.order_id}, User: {ret.user_id}) ---")
        print(f"Return Number: {ret.return_number}")
        print(f"Status: {ret.status}")
        print(f"Return Items: {len(ret.return_items)}")
        
        for item in ret.return_items:
            print(f"\n  Return Item ID: {item.id}")
            print(f"    Order Item ID: {item.order_item_id}")
            print(f"    Product ID: {item.product_id}")
            
            # Get the product
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                print(f"    Product: {product.title}")
                print(f"    Product Seller ID: {product.seller_id}")
                
                # Get seller info
                seller = db.query(User).filter(User.id == product.seller_id).first()
                if seller:
                    print(f"    Seller: {seller.username} (ID: {seller.id})")
            else:
                print(f"    ⚠️ Product not found!")
    
    print("\n" + "="*80)
    print("CHECKING SELLER QUERY")
    print("="*80)
    
    # Get all users who are sellers (have products)
    sellers = db.query(User).join(Product, User.id == Product.seller_id).distinct().all()
    
    print(f"\nTotal Sellers with Products: {len(sellers)}")
    for seller in sellers:
        print(f"\nSeller: {seller.username} (ID: {seller.id})")
        
        # Try the same query as the API endpoint
        from sqlalchemy.orm import joinedload
        seller_returns = db.query(Return)\
            .join(ReturnItem)\
            .join(Product, ReturnItem.product_id == Product.id)\
            .filter(Product.seller_id == seller.id)\
            .options(joinedload(Return.return_items))\
            .distinct()\
            .all()
        
        print(f"  Returns for this seller: {len(seller_returns)}")
        for sr in seller_returns:
            print(f"    - Return #{sr.return_number} (Order: {sr.order_id})")
    
    print("\n✅ Debug complete!\n")
    
finally:
    db.close()
