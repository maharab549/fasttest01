#!/usr/bin/env python
from app.database import SessionLocal
from app.models import Product

try:
    db = SessionLocal()
    products = db.query(Product).all()
    print(f"\n=== DATABASE CHECK ===")
    print(f"Total products in database: {len(products)}")
    
    if len(products) > 0:
        print("\nFirst 5 products:")
        for p in products[:5]:
            print(f"  ID: {p.id}, Title: {p.title}, Price: {p.price}")
    else:
        print("\n⚠️  NO PRODUCTS FOUND IN DATABASE!")
        print("You need to create or seed products first.")
    
    db.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
