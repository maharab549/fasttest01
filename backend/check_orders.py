"""
Check if there are any orders in the database
"""

import sqlite3
from pathlib import Path

def check_orders():
    """Check orders in database"""
    
    db_path = Path(__file__).parent / "marketplace.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all orders
        cursor.execute("""
            SELECT id, user_id, order_number, status, total_amount, discount_amount, discount_code, created_at
            FROM orders
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        orders = cursor.fetchall()
        
        if not orders:
            print("📭 No orders found in database")
        else:
            print(f"📦 Found {len(orders)} orders:\n")
            print("=" * 120)
            print(f"{'ID':<6} {'User':<6} {'Order Number':<20} {'Status':<12} {'Total':<10} {'Discount':<10} {'Code':<15} {'Created':<20}")
            print("=" * 120)
            for order in orders:
                id_, user_id, order_num, status, total, discount, code, created = order
                print(f"{id_:<6} {user_id:<6} {order_num:<20} {status:<12} ${total:<9.2f} ${discount:<9.2f} {str(code or 'N/A'):<15} {created}")
            print("=" * 120)
        
        # Get count by status
        cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
        status_counts = cursor.fetchall()
        
        print(f"\n📊 Orders by Status:")
        for status, count in status_counts:
            print(f"  • {status}: {count}")
        
        # Get users
        cursor.execute("SELECT DISTINCT user_id FROM orders ORDER BY user_id")
        user_ids = [row[0] for row in cursor.fetchall()]
        print(f"\n👥 Orders from Users: {user_ids}")
        
        conn.close()
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    print("🔍 Checking Orders in Database...\n")
    check_orders()
