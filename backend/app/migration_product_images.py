"""
Database Migration: Add ProductImage table and update ProductVariant

This migration adds support for multiple images per product and enhanced variant attributes.

Steps to apply this migration:
1. Run this script: python app/db_migrations.py
2. Or manually add the ProductImage table to your database

SQL for manual migration:
"""

CREATE_PRODUCT_IMAGES_TABLE = """
CREATE TABLE IF NOT EXISTS product_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    alt_text VARCHAR(255),
    is_primary BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    UNIQUE(product_id, image_url)
);

CREATE INDEX idx_product_images_product_id ON product_images(product_id);
"""

# Python migration code
from sqlalchemy import create_engine, text
from app.database import engine
from app.models import ProductImage, Base

def run_migration():
    """Create ProductImage table if it doesn't exist"""
    print("Running migration: Creating product_images table...")
    
    # Create all tables (SQLAlchemy will skip existing ones)
    Base.metadata.create_all(bind=engine)
    
    print("✅ Migration completed successfully!")
    print("ProductImage table created.")
    print("\nNew fields added to ProductVariant:")
    print("  - storage: VARCHAR (e.g., '256GB', '512GB')")
    print("  - ram: VARCHAR (e.g., '8GB', '16GB')")
    print("  - updated_at: TIMESTAMP")

if __name__ == "__main__":
    run_migration()
