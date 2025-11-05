"""
Migration script to add product snapshot fields to order_items table
This allows order items to retain product information even if the product is deleted
"""
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import engine

def migrate():
    """Add product_name and product_image columns to order_items table"""
    
    print("Starting migration: Adding product snapshot fields to order_items...")
    
    with engine.connect() as conn:
        # Add product_name column (SQLite compatible)
        try:
            conn.execute(text("ALTER TABLE order_items ADD COLUMN product_name VARCHAR"))
            conn.commit()
            print("✅ Added product_name column")
        except Exception as e:
            print(f"⚠️  product_name column might already exist: {e}")
            conn.rollback()
        
        # Add product_image column (SQLite compatible)
        try:
            conn.execute(text("ALTER TABLE order_items ADD COLUMN product_image VARCHAR"))
            conn.commit()
            print("✅ Added product_image column")
        except Exception as e:
            print(f"⚠️  product_image column might already exist: {e}")
            conn.rollback()
        
        # Update existing order items with product information (SQLite compatible)
        try:
            result = conn.execute(text("""
                UPDATE order_items
                SET product_name = (
                    SELECT title FROM products WHERE products.id = order_items.product_id
                ),
                product_image = (
                    SELECT json_extract(images, '$[0]') FROM products WHERE products.id = order_items.product_id
                )
                WHERE (product_name IS NULL OR product_name = '')
                AND product_id IN (SELECT id FROM products)
            """))
            conn.commit()
            print(f"✅ Updated {result.rowcount} existing order items with product information")
        except Exception as e:
            print(f"⚠️  Error updating existing order items: {e}")
            conn.rollback()
    
    print("Migration completed successfully! ✨")

if __name__ == "__main__":
    migrate()
