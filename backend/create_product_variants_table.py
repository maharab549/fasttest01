"""
Create the product_variants table
This creates the table that's missing from the database
"""

import sqlite3

def create_product_variants_table():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        print("Creating product_variants table...")
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            sku TEXT UNIQUE,
            variant_name TEXT,
            color TEXT,
            size TEXT,
            material TEXT,
            style TEXT,
            storage TEXT,
            ram TEXT,
            other_attributes TEXT,
            price_adjustment REAL DEFAULT 0.0,
            inventory_count INTEGER DEFAULT 0,
            images TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_product_id ON product_variants(product_id)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_sku ON product_variants(sku)''')
        
        conn.commit()
        print("✅ product_variants table created successfully!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_product_variants_table()
