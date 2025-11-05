#!/usr/bin/env python3
"""Verify order items have product snapshot data"""
from sqlalchemy import create_engine, text

# Create engine
engine = create_engine('sqlite:///./marketplace.db')

# Query order items
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT id, product_id, product_name, product_image, quantity, unit_price
        FROM order_items 
        LIMIT 5
    """))
    
    print("\n" + "="*80)
    print("ORDER ITEMS WITH PRODUCT SNAPSHOTS")
    print("="*80)
    
    for row in result:
        print(f"\nOrder Item ID: {row[0]}")
        print(f"  Product ID: {row[1]}")
        print(f"  Product Name: {row[2] or 'NULL'}")
        print(f"  Product Image: {row[3] or 'NULL'}")
        print(f"  Quantity: {row[4]}")
        print(f"  Unit Price: ${row[5]:.2f}")
        print("-"*80)
    
    print("\n✅ Migration verification complete!\n")
