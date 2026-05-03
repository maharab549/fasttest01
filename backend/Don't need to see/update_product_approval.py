"""
Update existing products to set approval_status to 'approved'
This is needed after adding the product approval feature
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine, SessionLocal

def update_product_approval_status():
    """Update all existing products to be approved by default"""
    db = SessionLocal()
    try:
        # Update all products with NULL or pending approval_status to approved
        result = db.execute(
            text("""
                UPDATE products 
                SET approval_status = 'approved' 
                WHERE approval_status IS NULL OR approval_status = 'pending'
            """)
        )
        db.commit()
        rows_affected = result.rowcount if hasattr(result, 'rowcount') else 'unknown'
        print(f"✅ Updated {rows_affected} products to approved status")
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Updating product approval status...")
    update_product_approval_status()
    print("Done!")
