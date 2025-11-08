"""
Migration Script: Add Discount Columns to Orders Table
This script adds the missing columns to the orders table to support the discount/redemption feature.
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database():
    """Add discount-related columns to the orders table"""
    
    # Get the database path
    db_path = Path(__file__).parent / "marketplace.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(orders)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        columns_to_add = [
            ("discount_amount", "REAL DEFAULT 0.0"),
            ("discount_code", "TEXT"),
            ("applied_redemption_id", "INTEGER"),
        ]
        
        added_count = 0
        for col_name, col_definition in columns_to_add:
            if col_name in existing_columns:
                print(f"⏭️  Column '{col_name}' already exists, skipping...")
            else:
                print(f"Adding column '{col_name}'...")
                cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_definition}")
                added_count += 1
        
        conn.commit()
        conn.close()
        
        if added_count > 0:
            print(f"\n✅ Migration successful! Added {added_count} column(s)")
            return True
        else:
            print("\n✅ All columns already exist - no migration needed")
            return True
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Starting database migration...")
    print("=" * 50)
    
    success = migrate_database()
    
    print("=" * 50)
    if success:
        print("✨ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)
