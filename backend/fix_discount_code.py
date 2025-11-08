import sqlite3
from datetime import datetime

DB_PATH = "app/database.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n" + "="*80)
print("DIAGNOSING DISC-EAAE2CA9 ISSUE")
print("="*80 + "\n")

# Check if code exists
cursor.execute("""
    SELECT id, loyalty_account_id, reward_code, reward_value, status, 
           order_id, used_at, expires_at, created_at
    FROM redemptions
    WHERE reward_code = 'DISC-EAAE2CA9'
""")

result = cursor.fetchone()

if result:
    redemption_id, acct_id, code, value, status, order_id, used_at, expires_at, created_at = result
    
    print(f"✓ Code found in database!")
    print(f"\n  Redemption ID: {redemption_id}")
    print(f"  Account ID: {acct_id}")
    print(f"  Code: {code}")
    print(f"  Value: ${value}")
    print(f"  Status: {status}")
    print(f"  Order ID: {order_id}")
    print(f"  Used At: {used_at}")
    print(f"  Expires At: {expires_at}")
    print(f"  Created At: {created_at}")
    
    # Check if there are orders with this code
    cursor.execute("""
        SELECT id, total_amount, discount_code, discount_amount, applied_redemption_id 
        FROM orders
        WHERE discount_code = 'DISC-EAAE2CA9'
        ORDER BY id DESC
    """)
    
    orders = cursor.fetchall()
    
    print(f"\n  Orders using this code: {len(orders)}")
    
    if orders:
        for i, (order_id2, total, disc_code, disc_amt, redemp_id) in enumerate(orders, 1):
            print(f"\n    Order {i}:")
            print(f"      ID: {order_id2}")
            print(f"      Total: ${total}")
            print(f"      Discount Amount: ${disc_amt if disc_amt else 'None'}")
            print(f"      Applied Redemption ID: {redemp_id}")
            
            # This is the expected redemption ID link
            if redemp_id == redemption_id:
                print(f"      ✓ Correctly linked to this redemption")
            else:
                print(f"      ✗ NOT linked to this redemption (linked to {redemp_id})")
    else:
        print("      None found")
    
    # Now diagnose the issue
    print("\n" + "="*80)
    print("DIAGNOSIS")
    print("="*80 + "\n")
    
    if status == "used" and order_id is not None and used_at is not None:
        print("✓ Code status is CORRECT:")
        print(f"  - Status: used")
        print(f"  - Linked to order: {order_id}")
        print(f"  - Used date: {used_at}")
        print("\n  The backend is working correctly!")
        
    elif status == "active" and order_id is None:
        print("✗ PROBLEM FOUND - Code not marked as used!")
        print(f"  - Status: active (should be 'used')")
        print(f"  - Order ID: None (should be linked)")
        print(f"  - Used At: None (should have timestamp)")
        
        if not orders:
            print("\n  Root cause: NO ORDERS exist with this code")
            print("  - Order may not have been created successfully")
            print("  - Or discount code not applied in checkout")
        else:
            print(f"\n  Root cause: Order exists but redemption not updated")
            print("  - Order was created with discount")
            print("  - But backend code didn't mark redemption as used")
            print("  - Likely a bug or race condition")
            
            # Suggest fix
            print(f"\n  FIXING THIS NOW...")
            order_to_link = orders[0][0]  # First order ID
            
            cursor.execute("""
                UPDATE redemptions
                SET status = 'used', 
                    order_id = ?, 
                    used_at = ?
                WHERE reward_code = 'DISC-EAAE2CA9'
            """, (order_to_link, datetime.utcnow()))
            
            conn.commit()
            
            print(f"  ✓ Updated redemption {redemption_id}:")
            print(f"    - Status: changed to 'used'")
            print(f"    - Linked to Order: {order_to_link}")
            print(f"    - Used At: {datetime.utcnow()}")
    else:
        print(f"? Unexpected state:")
        print(f"  - Status: {status}")
        print(f"  - Order ID: {order_id}")
        print(f"  - Used At: {used_at}")
        print(f"  - This is unusual, please review manually")

else:
    print("✗ Code NOT FOUND in database!")
    print("  The reward code DISC-EAAE2CA9 does not exist.")
    print("  It may have been deleted or never created.")

conn.close()

print("\n" + "="*80)
