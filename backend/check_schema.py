import sqlite3
import json

conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# Get table info
cursor.execute("PRAGMA table_info(product_variants);")
columns = cursor.fetchall()

print("=" * 60)
print("ACTUAL DATABASE SCHEMA - product_variants table")
print("=" * 60)
for col in columns:
    print(f"  {col[1]:30} | {col[2]:15} | NULL: {col[3]}")

print("\n" + "=" * 60)
print("CHECKING FOR DATA IN storage AND ram COLUMNS")
print("=" * 60)

# Check if storage and ram have any non-null values
cursor.execute("SELECT COUNT(*) FROM product_variants WHERE storage IS NOT NULL;")
storage_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM product_variants WHERE ram IS NOT NULL;")
ram_count = cursor.fetchone()[0]

print(f"Rows with storage data: {storage_count}")
print(f"Rows with ram data: {ram_count}")

# Check a sample
cursor.execute("SELECT id, product_id, storage, ram FROM product_variants LIMIT 5;")
rows = cursor.fetchall()
print("\nSample data:")
print(rows)

conn.close()
