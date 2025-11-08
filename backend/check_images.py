import sqlite3

conn = sqlite3.connect('marketplace.db')
cursor = conn.cursor()

# Check the product
cursor.execute("SELECT id, slug, title, images FROM products WHERE slug = 'dzcxz-6a6add'")
row = cursor.fetchone()

if row:
    print(f'Product ID: {row[0]}')
    print(f'Slug: {row[1]}')
    print(f'Title: {row[2]}')
    print(f'Images stored in product: {row[3]}')
else:
    print("Product not found")

# Check all images in product_images table
print("\n--- All images in product_images table ---")
cursor.execute("SELECT COUNT(*) FROM product_images")
count = cursor.fetchone()[0]
print(f'Total images: {count}')

if count > 0:
    cursor.execute("SELECT id, product_id, image_url FROM product_images LIMIT 20")
    rows = cursor.fetchall()
    for row in rows:
        print(f'Image ID: {row[0]}, Product ID: {row[1]}, URL: {row[2]}')

conn.close()
