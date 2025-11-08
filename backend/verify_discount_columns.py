"""
Verify the database schema to ensure migration was applied
"""

import sqlite3
from pathlib import Path

def verify_schema():
    """Check if all required columns exist in orders table"""
    
    db_path = Path(__file__).parent / "marketplace.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all columns in orders table
        cursor.execute("PRAGMA table_info(orders)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # name -> type
        
        print("📋 Orders Table Columns:")
        print("=" * 50)
        for col_name, col_type in sorted(columns.items()):
            print(f"  ✓ {col_name:<30} {col_type}")
        
        print("\n🔍 Checking for required discount columns:")
        print("=" * 50)
        
        required_columns = {
            'discount_code': 'TEXT',
            'discount_amount': 'REAL',
            'applied_redemption_id': 'INTEGER'
        }
        
        all_exist = True
        for col_name, expected_type in required_columns.items():
            if col_name in columns:
                print(f"  ✅ {col_name:<30} EXISTS")
            else:
                print(f"  ❌ {col_name:<30} MISSING")
                all_exist = False
        
        conn.close()
        
        return all_exist
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying Database Schema...\n")
    success = verify_schema()
    if success:
        print("\n✅ All required columns exist!")
    else:
        print("\n⚠️  Some columns are missing!")
