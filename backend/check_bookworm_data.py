#!/usr/bin/env python3
"""Check bookworm seller data"""
import sqlite3

# Connect to database
conn = sqlite3.connect('marketplace.db')
cursor = conn.cursor()

print("\n" + "="*80)
print("CHECKING BOOKWORM SELLER DATA")
print("="*80)

# Get bookworm user ID
cursor.execute("SELECT id, username, email FROM users WHERE username = 'bookworm'")
seller = cursor.fetchone()

if not seller:
    print("\n❌ Bookworm user not found!")
    conn.close()
    exit(1)

seller_id, username, email = seller
print(f"\n✅ Seller found: {username} (ID: {seller_id}, Email: {email})")

# Get bookworm's products
cursor.execute("SELECT id, title, seller_id FROM products WHERE seller_id = ?", (seller_id,))
products = cursor.fetchall()

print(f"\n📦 Products sold by {username}: {len(products)}")
for product in products:
    print(f"  - Product ID {product[0]}: {product[1]}")

# Get all returns
cursor.execute("""
    SELECT r.id, r.return_number, r.order_id, r.user_id, r.status
    FROM returns r
""")
all_returns = cursor.fetchall()

print(f"\n📋 Total returns in database: {len(all_returns)}")

# Get returns with items
cursor.execute("""
    SELECT 
        r.id as return_id,
        r.return_number,
        r.order_id,
        r.user_id,
        r.status,
        ri.id as item_id,
        ri.product_id,
        ri.order_item_id,
        p.title as product_name,
        p.seller_id
    FROM returns r
    JOIN return_items ri ON r.id = ri.return_id
    LEFT JOIN products p ON ri.product_id = p.id
""")
return_details = cursor.fetchall()

print(f"\n📋 Return items details:")
for detail in return_details:
    return_id, return_number, order_id, user_id, status, item_id, product_id, order_item_id, product_name, product_seller_id = detail
    is_bookworm = "✅ BOOKWORM'S PRODUCT" if product_seller_id == seller_id else f"(Seller ID: {product_seller_id})"
    print(f"\n  Return #{return_number} (ID: {return_id})")
    print(f"    Order: {order_id}, Customer: {user_id}, Status: {status}")
    print(f"    Product ID: {product_id} - {product_name} {is_bookworm}")

# Now test the exact query used in the API
print(f"\n" + "="*80)
print("TESTING API QUERY")
print("="*80)

cursor.execute("""
    SELECT DISTINCT r.id, r.return_number, r.order_id, r.status
    FROM returns r
    JOIN return_items ri ON r.id = ri.return_id
    JOIN products p ON ri.product_id = p.id
    WHERE p.seller_id = ?
""", (seller_id,))

seller_returns = cursor.fetchall()

print(f"\n✅ Returns for bookworm (using API query): {len(seller_returns)}")
for ret in seller_returns:
    print(f"  - Return ID {ret[0]}: {ret[1]} (Order: {ret[2]}, Status: {ret[3]})")

conn.close()

print("\n" + "="*80)
print("✅ Check complete!")
print("="*80 + "\n")
