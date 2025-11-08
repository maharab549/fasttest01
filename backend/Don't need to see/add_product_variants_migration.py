"""
Add product variants table for colors, sizes, and other options
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.database import Base

# This is a migration script to add product variants support

"""
Product Variants Structure:

Product
  - id
  - title
  - description
  - base_price
  - has_variants (boolean)
  
ProductVariant
  - id
  - product_id (FK)
  - sku (unique identifier)
  - color
  - size
  - material
  - style
  - other_attributes (JSON)
  - price_adjustment (can be + or -)
  - inventory_count
  - images (JSON - specific images for this variant)
  - is_active

Example:
Product: "T-Shirt" 
  Variants:
    - Red, Small, Cotton - $19.99
    - Red, Medium, Cotton - $19.99
    - Blue, Small, Cotton - $22.99
    - Blue, Large, Polyester - $24.99
"""

SQL_COMMANDS = """
-- Create product_variants table
CREATE TABLE IF NOT EXISTS product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    sku VARCHAR UNIQUE,
    variant_name VARCHAR,
    color VARCHAR,
    size VARCHAR,
    material VARCHAR,
    style VARCHAR,
    other_attributes TEXT,  -- JSON string for custom attributes
    price_adjustment FLOAT DEFAULT 0.0,
    inventory_count INTEGER DEFAULT 0,
    images TEXT,  -- JSON array of image URLs
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_product_variants_sku ON product_variants(sku);

-- Add has_variants column to products table
ALTER TABLE products ADD COLUMN has_variants BOOLEAN DEFAULT 0;

-- Create product_variant_options table for defining available options
CREATE TABLE IF NOT EXISTS product_variant_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    option_type VARCHAR NOT NULL,  -- 'color', 'size', 'material', etc.
    option_value VARCHAR NOT NULL,
    display_order INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_variant_options_product_id ON product_variant_options(product_id);
"""

print("Product Variants Migration SQL:")
print(SQL_COMMANDS)
print("\n\nTo apply this migration, run:")
print("python add_product_variants.py")
