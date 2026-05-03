"""
Add variant_id column to order_items and cart_items tables
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "marketplace.db"

def add_variant_columns():
    print("=" * 60)
    print("ADDING VARIANT SUPPORT TO ORDERS AND CART")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check current columns
        cursor.execute("PRAGMA table_info(order_items)")
        order_item_cols = [col[1] for col in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(cart_items)")
        cart_item_cols = [col[1] for col in cursor.fetchall()]
        
        # Add variant_id to order_items
        if 'variant_id' not in order_item_cols:
            print("\n✅ Adding 'variant_id' to order_items table...")
            cursor.execute("ALTER TABLE order_items ADD COLUMN variant_id INTEGER")
            cursor.execute("ALTER TABLE order_items ADD COLUMN variant_details TEXT")  # JSON string
            print("   Columns added successfully!")
        else:
            print("\n✓ order_items already has variant columns")
        
        # Add variant_id to cart_items
        if 'variant_id' not in cart_item_cols:
            print("\n✅ Adding 'variant_id' to cart_items table...")
            cursor.execute("ALTER TABLE cart_items ADD COLUMN variant_id INTEGER")
            print("   Column added successfully!")
        else:
            print("\n✓ cart_items already has variant column")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ VARIANT COLUMNS ADDED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_variant_columns()
