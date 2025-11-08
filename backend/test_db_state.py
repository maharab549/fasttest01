import sqlite3

conn = sqlite3.connect('marketplace.db')
cursor = conn.cursor()

print("=" * 60)
print("PRODUCT IMAGES IN DATABASE")
print("=" * 60)
cursor.execute('SELECT COUNT(*) FROM product_images')
count = cursor.fetchone()[0]
print(f'Total ProductImages: {count}')

if count > 0:
    print("\nRecent ProductImages:")
    cursor.execute('SELECT id, product_id, image_url, created_at FROM product_images ORDER BY created_at DESC LIMIT 10')
    for row in cursor.fetchall():
        print(f'  ID={row[0]}, Product={row[1]}, URL={row[2]}, Created={row[3]}')

# Check a specific product's images field
print("\n" + "=" * 60)
print("PRODUCTS IMAGES FIELD (JSON)")
print("=" * 60)
cursor.execute('SELECT id, title, images FROM products WHERE id = 4')
result = cursor.fetchone()
if result:
    print(f'Product 4: {result[1]}')
    print(f'Images field: {result[2]}')

# Check if there are any featured products
print("\n" + "=" * 60)
print("FEATURED PRODUCTS")
print("=" * 60)
cursor.execute('SELECT id, title, is_featured, is_active, approval_status FROM products WHERE is_featured = 1 LIMIT 5')
featured = cursor.fetchall()
print(f'Total featured products: {cursor.rowcount}')
for row in featured:
    print(f'  ID={row[0]}, Title={row[1]}, Featured={row[2]}, Active={row[3]}, Status={row[4]}')

conn.close()
