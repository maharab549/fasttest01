#!/usr/bin/env python3
"""Clean up large/suspicious orders from the database"""

from app.database import SessionLocal
from app.models import Order
import sys

def cleanup_large_orders(threshold=1000000):
    """Remove orders with total_amount greater than threshold"""
    db = SessionLocal()
    
    try:
        # Find large orders
        large_orders = db.query(Order).filter(Order.total_amount > threshold).all()
        
        if not large_orders:
            print(f"✓ No orders found with amount > {threshold}")
            return True
        
        print(f"Found {len(large_orders)} orders with amount > {threshold}:")
        for order in large_orders:
            print(f"  - Order #{order.id}: ${order.total_amount} (User: {order.user_id})")
        
        # Delete large orders
        deleted_count = len(large_orders)
        for order in large_orders:
            db.delete(order)
        
        db.commit()
        print(f"\n✓ Successfully deleted {deleted_count} large orders")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error during cleanup: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # Set threshold (default: 1 million)
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 1000000
    
    print(f"Cleaning up orders with amount > ${threshold}...")
    success = cleanup_large_orders(threshold)
    sys.exit(0 if success else 1)
