import sqlite3
import json
from datetime import datetime

DB_PATH = "app/database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("CHECKING REDEMPTION CODE: DISC-EAAE2CA9")
print("=" * 80)

# Find the specific code
cursor.execute("""
    SELECT id, loyalty_account_id, reward_code, reward_value, status, 
           order_id, used_at, expires_at, created_at
    FROM redemptions
    WHERE reward_code = 'DISC-EAAE2CA9'
""")

result = cursor.fetchone()

if result:
    redemption_id, acct_id, code, value, status, order_id, used_at, expires_at, created_at = result
    print(f"\n✓ Code found!")
    print(f"  ID: {redemption_id}")
    print(f"  Account ID: {acct_id}")
    print(f"  Code: {code}")
    print(f"  Value: ${value}")
    print(f"  Status: {status}")
    print(f"  Order ID: {order_id}")
    print(f"  Used At: {used_at}")
    print(f"  Expires At: {expires_at}")
    print(f"  Created: {created_at}")
    
    if status == 'active' and order_id is None:
        print("\n⚠️  ISSUE FOUND:")
        print("  - Status is still 'active'")
        print("  - No order_id linked")
        print("  - used_at is empty")
        print("  → Code was NOT marked as used after order placement")
    elif status == 'used':
        print("\n✓ Code is marked as used")
        print(f"  Linked to Order: {order_id}")
        print(f"  Used date: {used_at}")
else:
    print("\n✗ Code not found in database!")

# Check if there's an order with this discount code
print("\n" + "=" * 80)
print("CHECKING ORDERS WITH THIS CODE")
print("=" * 80)

cursor.execute("""
    SELECT id, order_number, user_id, total_amount, discount_code, 
           discount_amount, applied_redemption_id, created_at
    FROM orders
    WHERE discount_code = 'DISC-EAAE2CA9'
    ORDER BY created_at DESC
    LIMIT 5
""")

orders = cursor.fetchall()

if orders:
    print(f"\n✓ Found {len(orders)} order(s) with this code:")
    for order_id, order_num, user_id, total, disc_code, disc_amt, redemp_id, created in orders:
        print(f"\n  Order #{order_num} (ID: {order_id})")
        print(f"    User: {user_id}")
        print(f"    Total: ${total}")
        print(f"    Discount Code: {disc_code}")
        print(f"    Discount Amount: ${disc_amt}")
        print(f"    Applied Redemption ID: {redemp_id}")
        print(f"    Created: {created}")
else:
    print("\n✗ No orders found with this code")

# Check all orders for this user to see recent activity
print("\n" + "=" * 80)
print("CHECKING USER'S RECENT ORDERS")
print("=" * 80)

cursor.execute("""
    SELECT id, user_id FROM loyalty_accounts WHERE id IN (
        SELECT loyalty_account_id FROM redemptions WHERE reward_code = 'DISC-EAAE2CA9'
    )
""")

acct = cursor.fetchone()
if acct:
    acct_id, user_id = acct
    print(f"\nUser ID: {user_id}")
    
    cursor.execute("""
        SELECT id, order_number, total_amount, discount_code, discount_amount, created_at
        FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (user_id,))
    
    user_orders = cursor.fetchall()
    print(f"\nRecent orders ({len(user_orders)}):")
    for order_id, order_num, total, disc_code, disc_amt, created in user_orders:
        print(f"  Order #{order_num}: Total=${total}, Discount={'$' + str(disc_amt) if disc_amt else 'None'}, Created={created}")

conn.close()

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("If the code is still 'active':")
print("1. Manually update the redemption to 'used' status")
print("2. Update the order placement code to properly mark rewards")
print("=" * 80)
