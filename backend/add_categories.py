#!/usr/bin/env python3
"""
Script to add all 31 categories to the database
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

def add_all_categories():
    """Add all 31 categories to the database"""
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        categories_data = [
            {"name": "Electronics", "slug": "electronics", "description": "Electronic devices and gadgets"},
            {"name": "Clothing", "slug": "clothing", "description": "Fashion and apparel"},
            {"name": "Books", "slug": "books", "description": "Books and literature"},
            {"name": "Home & Garden", "slug": "home-garden", "description": "Home improvement and gardening"},
            {"name": "Sports", "slug": "sports", "description": "Sports and outdoor equipment"},
            {"name": "Toys", "slug": "toys", "description": "Toys and games"},
            {"name": "Computers", "slug": "computers", "description": "Desktops, laptops, and accessories"},
            {"name": "Watches", "slug": "watches", "description": "Wrist watches and smartwatches"},
            {"name": "Photography", "slug": "photography", "description": "Cameras and photography gear"},
            {"name": "Audio", "slug": "audio", "description": "Speakers, headphones, and audio equipment"},
            {"name": "Beauty", "slug": "beauty", "description": "Beauty and personal care"},
            {"name": "Health", "slug": "health", "description": "Health and wellness products"},
            {"name": "Groceries", "slug": "groceries", "description": "Food and grocery items"},
            {"name": "Automotive", "slug": "automotive", "description": "Car accessories and parts"},
            {"name": "Jewelry", "slug": "jewelry", "description": "Jewelry and accessories"},
            {"name": "Baby & Kids", "slug": "baby-kids", "description": "Baby and kids products"},
            {"name": "Office Supplies", "slug": "office-supplies", "description": "Office and school supplies"},
            {"name": "Pet Supplies", "slug": "pet-supplies", "description": "Pet food and accessories"},
            {"name": "Garden", "slug": "garden", "description": "Gardening tools and plants"},
            {"name": "Furniture", "slug": "furniture", "description": "Home and office furniture"},
            {"name": "Footwear", "slug": "footwear", "description": "Shoes, sandals, and boots"},
            {"name": "Bags & Luggage", "slug": "bags-luggage", "description": "Bags, backpacks, and luggage"},
            {"name": "Musical Instruments", "slug": "musical-instruments", "description": "Instruments and music gear"},
            {"name": "Crafts", "slug": "crafts", "description": "Arts and crafts supplies"},
            {"name": "Travel", "slug": "travel", "description": "Travel accessories and gear"},
            {"name": "Appliances", "slug": "appliances", "description": "Home and kitchen appliances"},
            {"name": "Stationery", "slug": "stationery", "description": "Stationery and writing supplies"},
            {"name": "Outdoor", "slug": "outdoor", "description": "Outdoor and camping gear"},
            {"name": "Mobile Accessories", "slug": "mobile-accessories", "description": "Phone cases, chargers, and more"},
            {"name": "Gaming", "slug": "gaming", "description": "Video games and gaming accessories"},
            {"name": "Home Decor", "slug": "home-decor", "description": "Decorative items for home"},
        ]
        
        added_count = 0
        for cat_data in categories_data:
            existing_cat = db.query(models.Category).filter(models.Category.slug == cat_data["slug"]).first()
            if not existing_cat:
                category = models.Category(**cat_data)
                db.add(category)
                added_count += 1
                print(f"Added category: {cat_data['name']}")
            else:
                print(f"Category already exists: {cat_data['name']}")
        
        db.commit()
        
        # Count total categories
        total_categories = db.query(models.Category).count()
        print(f"\n✓ Total categories in database: {total_categories}")
        print(f"✓ New categories added: {added_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Adding all categories to database...")
    add_all_categories()
    print("Done!")
