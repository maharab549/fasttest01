import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Product, Category, User
import random

def main():
    db = SessionLocal()
    
    # Get existing categories
    categories = db.query(Category).all()
    
    # Get seller users
    sellers = db.query(User).filter(User.is_seller == True).all()
    
    if not sellers:
        print("No sellers found!")
        return
    
    print(f"Found {len(sellers)} sellers and {len(categories)} categories")
    
    # Simple product data
    products_data = [
        {"title": "Wireless Headphones", "price": 99.99, "description": "High-quality wireless headphones"},
        {"title": "Smart Watch", "price": 199.99, "description": "Advanced fitness tracking smartwatch"},
        {"title": "Laptop Computer", "price": 899.99, "description": "Powerful laptop for work and gaming"},
        {"title": "Smartphone", "price": 699.99, "description": "Latest smartphone with advanced features"},
        {"title": "Running Shoes", "price": 79.99, "description": "Comfortable running shoes for athletes"},
        {"title": "Coffee Maker", "price": 129.99, "description": "Automatic coffee maker with timer"},
        {"title": "Desk Chair", "price": 159.99, "description": "Ergonomic office chair"},
        {"title": "Bluetooth Speaker", "price": 49.99, "description": "Portable wireless speaker"},
    ]
    
    count = 0
    for i in range(100):  # Create 100 products for now
        for base_product in products_data:
            if count >= 100:
                break
                
            seller = random.choice(sellers)
            category = random.choice(categories)
            
            # Create unique title
            title = f"{base_product['title']} {random.choice(['Pro', 'Max', 'Plus', 'Elite', 'Premium'])} {i+1}"
            slug = title.lower().replace(' ', '-').replace(',', '')
            
            product = Product(
                title=title,
                slug=f"{slug}-{count}",
                description=base_product['description'],
                price=base_product['price'] * random.uniform(0.8, 1.5),
                category_id=category.id,
                seller_id=1,  # Use first seller
                inventory_count=random.randint(10, 100),
                is_active=True,
                sku=f"SKU-{count:06d}"
            )
            
            db.add(product)
            count += 1
            
            if count % 20 == 0:
                print(f"Created {count} products...")
                db.commit()
    
    db.commit()
    print(f"Successfully created {count} products!")
    db.close()

if __name__ == "__main__":
    main()
