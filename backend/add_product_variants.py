"""
Apply product variants migration to the database
"""
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "marketplace.db"

def apply_migration():
    print("=" * 60)
    print("APPLYING PRODUCT VARIANTS MIGRATION")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add has_variants column if it doesn't exist
        if 'has_variants' not in columns:
            print("\n✅ Adding 'has_variants' column to products table...")
            cursor.execute("ALTER TABLE products ADD COLUMN has_variants BOOLEAN DEFAULT 0")
            print("   Column added successfully!")
        else:
            print("\n✓ 'has_variants' column already exists")
        
        # Create product_variants table
        print("\n✅ Creating 'product_variants' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                sku VARCHAR UNIQUE,
                variant_name VARCHAR,
                color VARCHAR,
                size VARCHAR,
                material VARCHAR,
                style VARCHAR,
                other_attributes TEXT,
                price_adjustment FLOAT DEFAULT 0.0,
                inventory_count INTEGER DEFAULT 0,
                images TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        """)
        print("   Table created successfully!")
        
        # Create indexes
        print("\n✅ Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_variants_sku ON product_variants(sku)")
        print("   Indexes created successfully!")
        
        # Create product_variant_options table
        print("\n✅ Creating 'product_variant_options' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_variant_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                option_type VARCHAR NOT NULL,
                option_value VARCHAR NOT NULL,
                display_order INTEGER DEFAULT 0,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        """)
        print("   Table created successfully!")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_variant_options_product_id ON product_variant_options(product_id)")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%variant%'")
        tables = cursor.fetchall()
        print("\n📊 Variant tables in database:")
        for table in tables:
            print(f"   - {table[0]}")
            
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration()
