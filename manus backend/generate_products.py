#!/usr/bin/env python3
"""
Script to generate 500+ products across all categories for the marketplace
"""

import os
import sys
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import models, crud
from app.models import Product, Category, User

# Product data templates
ELECTRONICS_PRODUCTS = [
    {"name": "Wireless Bluetooth Headphones", "base_price": 79.99, "description": "High-quality wireless headphones with noise cancellation and 30-hour battery life."},
    {"name": "Smart Fitness Watch", "base_price": 199.99, "description": "Advanced fitness tracking with heart rate monitor, GPS, and smartphone connectivity."},
    {"name": "Gaming Laptop", "base_price": 1299.99, "description": "High-performance gaming laptop with RTX graphics and 16GB RAM."},
    {"name": "Smartphone", "base_price": 699.99, "description": "Latest smartphone with advanced camera system and 5G connectivity."},
    {"name": "Tablet", "base_price": 329.99, "description": "10-inch tablet with high-resolution display and all-day battery life."},
    {"name": "Wireless Earbuds", "base_price": 149.99, "description": "True wireless earbuds with active noise cancellation."},
    {"name": "Smart Speaker", "base_price": 99.99, "description": "Voice-controlled smart speaker with premium sound quality."},
    {"name": "4K Monitor", "base_price": 299.99, "description": "27-inch 4K monitor with HDR support and USB-C connectivity."},
    {"name": "Mechanical Keyboard", "base_price": 129.99, "description": "RGB mechanical gaming keyboard with customizable switches."},
    {"name": "Wireless Mouse", "base_price": 59.99, "description": "Ergonomic wireless mouse with precision tracking."},
]

CLOTHING_PRODUCTS = [
    {"name": "Running Shoes", "base_price": 89.99, "description": "Lightweight running shoes with advanced cushioning technology."},
    {"name": "Casual T-Shirt", "base_price": 19.99, "description": "Comfortable cotton t-shirt in various colors and sizes."},
    {"name": "Denim Jeans", "base_price": 59.99, "description": "Classic fit denim jeans with premium quality fabric."},
    {"name": "Winter Jacket", "base_price": 129.99, "description": "Warm winter jacket with water-resistant coating."},
    {"name": "Athletic Shorts", "base_price": 29.99, "description": "Moisture-wicking athletic shorts for sports and fitness."},
    {"name": "Dress Shirt", "base_price": 49.99, "description": "Professional dress shirt for business and formal occasions."},
    {"name": "Sneakers", "base_price": 79.99, "description": "Stylish sneakers for everyday wear and casual outings."},
    {"name": "Hoodie", "base_price": 39.99, "description": "Comfortable hoodie with soft fleece lining."},
    {"name": "Yoga Pants", "base_price": 34.99, "description": "Flexible yoga pants with four-way stretch fabric."},
    {"name": "Baseball Cap", "base_price": 24.99, "description": "Adjustable baseball cap with embroidered logo."},
]

HOME_PRODUCTS = [
    {"name": "Coffee Maker", "base_price": 89.99, "description": "Programmable coffee maker with thermal carafe and auto-brew feature."},
    {"name": "Air Purifier", "base_price": 149.99, "description": "HEPA air purifier for clean and fresh indoor air."},
    {"name": "Vacuum Cleaner", "base_price": 199.99, "description": "Powerful vacuum cleaner with multiple attachments."},
    {"name": "Bed Sheets Set", "base_price": 49.99, "description": "Soft and comfortable bed sheets made from premium cotton."},
    {"name": "Kitchen Knife Set", "base_price": 79.99, "description": "Professional kitchen knife set with wooden block."},
    {"name": "Throw Pillow", "base_price": 19.99, "description": "Decorative throw pillow with removable cover."},
    {"name": "Table Lamp", "base_price": 39.99, "description": "Modern table lamp with adjustable brightness."},
    {"name": "Storage Basket", "base_price": 24.99, "description": "Woven storage basket for organizing home items."},
    {"name": "Wall Clock", "base_price": 29.99, "description": "Silent wall clock with modern design."},
    {"name": "Candle Set", "base_price": 34.99, "description": "Scented candle set with relaxing fragrances."},
]

BOOKS_PRODUCTS = [
    {"name": "Programming Guide", "base_price": 39.99, "description": "Comprehensive guide to modern programming languages and techniques."},
    {"name": "Cookbook", "base_price": 24.99, "description": "Collection of delicious recipes for home cooking."},
    {"name": "Self-Help Book", "base_price": 16.99, "description": "Inspirational book for personal development and growth."},
    {"name": "Science Fiction Novel", "base_price": 14.99, "description": "Thrilling science fiction adventure in a futuristic world."},
    {"name": "History Book", "base_price": 29.99, "description": "Detailed exploration of historical events and civilizations."},
    {"name": "Art Book", "base_price": 49.99, "description": "Beautiful collection of artwork with high-quality illustrations."},
    {"name": "Travel Guide", "base_price": 19.99, "description": "Complete travel guide with tips and recommendations."},
    {"name": "Biography", "base_price": 22.99, "description": "Inspiring biography of a remarkable historical figure."},
    {"name": "Children's Book", "base_price": 12.99, "description": "Colorful children's book with engaging stories and illustrations."},
    {"name": "Business Book", "base_price": 27.99, "description": "Strategic insights for business success and leadership."},
]

SPORTS_PRODUCTS = [
    {"name": "Yoga Mat", "base_price": 29.99, "description": "Non-slip yoga mat with extra cushioning for comfort."},
    {"name": "Dumbbells Set", "base_price": 89.99, "description": "Adjustable dumbbells set for home fitness workouts."},
    {"name": "Basketball", "base_price": 24.99, "description": "Official size basketball with superior grip and durability."},
    {"name": "Tennis Racket", "base_price": 79.99, "description": "Professional tennis racket with lightweight frame."},
    {"name": "Swimming Goggles", "base_price": 19.99, "description": "Anti-fog swimming goggles with UV protection."},
    {"name": "Resistance Bands", "base_price": 15.99, "description": "Set of resistance bands for strength training exercises."},
    {"name": "Soccer Ball", "base_price": 29.99, "description": "FIFA-approved soccer ball with excellent flight characteristics."},
    {"name": "Cycling Helmet", "base_price": 49.99, "description": "Lightweight cycling helmet with ventilation system."},
    {"name": "Water Bottle", "base_price": 14.99, "description": "Insulated water bottle that keeps drinks cold for 24 hours."},
    {"name": "Fitness Tracker", "base_price": 59.99, "description": "Activity tracker with step counter and sleep monitoring."},
]

BEAUTY_PRODUCTS = [
    {"name": "Moisturizing Cream", "base_price": 24.99, "description": "Hydrating moisturizing cream for all skin types."},
    {"name": "Shampoo", "base_price": 12.99, "description": "Nourishing shampoo for healthy and shiny hair."},
    {"name": "Lipstick", "base_price": 18.99, "description": "Long-lasting lipstick in vibrant colors."},
    {"name": "Face Mask", "base_price": 8.99, "description": "Rejuvenating face mask with natural ingredients."},
    {"name": "Perfume", "base_price": 49.99, "description": "Elegant perfume with floral and citrus notes."},
    {"name": "Nail Polish", "base_price": 9.99, "description": "Quick-dry nail polish in trendy colors."},
    {"name": "Sunscreen", "base_price": 16.99, "description": "Broad-spectrum sunscreen with SPF 50 protection."},
    {"name": "Hair Conditioner", "base_price": 14.99, "description": "Deep conditioning treatment for smooth hair."},
    {"name": "Body Lotion", "base_price": 19.99, "description": "Luxurious body lotion with moisturizing formula."},
    {"name": "Makeup Brush Set", "base_price": 34.99, "description": "Professional makeup brush set with synthetic bristles."},
]

# Image mappings for products
PRODUCT_IMAGES = {
    "Wireless Bluetooth Headphones": "wireless-headphones.jpg",
    "Smart Fitness Watch": "smart-watch.jpg",
    "Gaming Laptop": "laptop.jpg",
    "Smartphone": "smartphone.jpg",
    "Running Shoes": "running-shoes.jpg",
}

def get_random_seller(db: Session):
    """Get a random seller from the database"""
    sellers = db.query(User).filter(User.is_seller == True).all()
    return random.choice(sellers) if sellers else None

def get_category_by_name(db: Session, name: str):
    """Get category by name"""
    return db.query(Category).filter(Category.name == name).first()

def generate_product_variants(base_product, count=10):
    """Generate variants of a base product"""
    variants = []
    
    for i in range(count):
        # Create price variations
        price_multiplier = random.uniform(0.8, 1.5)
        price = round(base_product["base_price"] * price_multiplier, 2)
        
        # Create name variations
        prefixes = ["Premium", "Deluxe", "Pro", "Ultra", "Advanced", "Classic", "Standard", "Elite"]
        suffixes = ["V2", "Plus", "Max", "Lite", "Edition", "Series", "Model"]
        
        name_variants = [
            base_product["name"],
            f"{random.choice(prefixes)} {base_product['name']}",
            f"{base_product['name']} {random.choice(suffixes)}",
            f"{base_product['name']} - {random.choice(['Black', 'White', 'Blue', 'Red', 'Silver'])}",
        ]
        
        variant = {
            "name": random.choice(name_variants),
            "price": price,
            "description": base_product["description"],
            "stock_quantity": random.randint(5, 100),
            "is_active": True,
            "is_featured": random.choice([True, False]) if random.random() < 0.2 else False,
        }
        
        # Add image if available
        if base_product["name"] in PRODUCT_IMAGES:
            variant["image_url"] = f"/uploads/{PRODUCT_IMAGES[base_product['name']]}"
        
        variants.append(variant)
    
    return variants

def main():
    """Generate 500+ products across all categories"""
    db = SessionLocal()
    
    try:
        # Get all categories
        categories = {
            "Electronics": get_category_by_name(db, "Electronics"),
            "Clothing": get_category_by_name(db, "Clothing"),
            "Home & Garden": get_category_by_name(db, "Home & Garden"),
            "Books": get_category_by_name(db, "Books"),
            "Sports": get_category_by_name(db, "Sports"),
            "Beauty": get_category_by_name(db, "Beauty"),
        }
        
        # Product templates by category
        category_products = {
            "Electronics": ELECTRONICS_PRODUCTS,
            "Clothing": CLOTHING_PRODUCTS,
            "Home & Garden": HOME_PRODUCTS,
            "Books": BOOKS_PRODUCTS,
            "Sports": SPORTS_PRODUCTS,
            "Beauty": BEAUTY_PRODUCTS,
        }
        
        total_products_created = 0
        
        for category_name, category in categories.items():
            if not category:
                print(f"Category {category_name} not found, skipping...")
                continue
                
            print(f"Generating products for {category_name}...")
            
            base_products = category_products[category_name]
            
            for base_product in base_products:
                # Generate 8-12 variants per base product
                variant_count = random.randint(8, 12)
                variants = generate_product_variants(base_product, variant_count)
                
                for variant in variants:
                    seller = get_random_seller(db)
                    if not seller:
                        print("No sellers found, skipping product creation...")
                        continue
                    
                    # Create product
                    timestamp = int(datetime.now().timestamp() * 1000)
                    random_num = random.randint(1000, 9999)
                    product_slug = f"{variant['name'].lower().replace(' ', '-')}-{timestamp}-{random_num}"
                    product = Product(
                        title=variant['name'],
                        slug=product_slug,
                        description=variant['description'],
                        short_description=variant['description'][:100] + "..." if len(variant['description']) > 100 else variant['description'],
                        price=variant['price'],
                        compare_price=variant['price'] * 1.2,
                        sku=f"SKU-{int(datetime.now().timestamp() * 1000)}-{random.randint(1000, 9999)}",
                        inventory_count=variant['stock_quantity'],
                        category_id=category.id,
                        seller_id=seller.id,
                        is_active=variant["is_active"],
                        is_featured=variant["is_featured"],
                        images=[variant.get("image_url")] if variant.get("image_url") else [],
                        rating=round(random.uniform(3.5, 5.0), 1),
                        review_count=random.randint(0, 50),
                        weight=random.uniform(0.1, 5.0)
                    )

                    
                    db.add(product)
                    total_products_created += 1
                    
                    if total_products_created % 50 == 0:
                        print(f"Created {total_products_created} products...")
                        db.commit()
        
        # Final commit
        db.commit()
        print(f"Successfully created {total_products_created} products!")
        
        # Print summary
        for category_name, category in categories.items():
            if category:
                count = db.query(Product).filter(Product.category_id == category.id).count()
                print(f"{category_name}: {count} products")
        
    except Exception as e:
        print(f"Error generating products: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

