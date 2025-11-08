"""Quick test to verify image saving works"""
import sqlite3

# Check current state
conn = sqlite3.connect('marketplace.db')
cursor = conn.cursor()

print("=== BEFORE TESTING ===")
cursor.execute('SELECT COUNT(*) FROM product_images')
count = cursor.fetchone()[0]
print(f"Total images in product_images table: {count}")

cursor.execute('SELECT COUNT(*) FROM products')
product_count = cursor.fetchone()[0]
print(f"Total products: {product_count}")

if product_count > 0:
    cursor.execute('SELECT id, name, images FROM products LIMIT 1')
    prod = cursor.fetchone()
    print(f"\nFirst product: ID={prod[0]}, Name={prod[1]}, Images={prod[2]}")

conn.close()

print("\n✓ Database check complete")
print("Note: To test uploading, use the frontend to upload an image to a product")
