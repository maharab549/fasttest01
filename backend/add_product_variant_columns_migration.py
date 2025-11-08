"""
Migration script to add missing columns to product_variants table.
"""
import sqlite3

DB_PATH = "marketplace.db"  # Correct path for backend directory

def add_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Add 'storage' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN storage TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("storage:", e)
    # Add 'ram' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN ram TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("ram:", e)
    # Add 'material' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN material TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("material:", e)
    # Add 'style' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN style TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("style:", e)
    # Add 'other_attributes' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN other_attributes TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("other_attributes:", e)
    # Add 'price_adjustment' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN price_adjustment REAL DEFAULT 0.0")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("price_adjustment:", e)
    # Add 'inventory_count' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN inventory_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("inventory_count:", e)
    # Add 'images' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN images TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("images:", e)
    # Add 'is_active' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN is_active BOOLEAN DEFAULT 1")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("is_active:", e)
    # Add 'created_at' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN created_at DATETIME")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("created_at:", e)
    # Add 'updated_at' column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE product_variants ADD COLUMN updated_at DATETIME")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e):
            print("updated_at:", e)
    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    add_columns()
