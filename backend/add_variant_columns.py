"""
Add missing columns to product_variants table
This script adds the storage and ram columns that were added to the model
"""

import sqlite3

def add_missing_columns():
    try:
        # Connect to the database
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        print("Checking product_variants table schema...")
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(product_variants)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        # Add missing columns if they don't exist
        missing_columns = []
        
        if 'storage' not in existing_columns:
            print("Adding 'storage' column...")
            cursor.execute("ALTER TABLE product_variants ADD COLUMN storage TEXT DEFAULT NULL")
            missing_columns.append('storage')
        
        if 'ram' not in existing_columns:
            print("Adding 'ram' column...")
            cursor.execute("ALTER TABLE product_variants ADD COLUMN ram TEXT DEFAULT NULL")
            missing_columns.append('ram')
        
        if missing_columns:
            conn.commit()
            print(f"✅ Successfully added columns: {missing_columns}")
        else:
            print("✅ All required columns already exist!")
        
        # Verify
        cursor.execute("PRAGMA table_info(product_variants)")
        columns_after = [row[1] for row in cursor.fetchall()]
        print(f"Columns after migration: {columns_after}")
        
        conn.close()
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    add_missing_columns()
