import sqlite3

DB_PATH = 'D:/All github project/fasttest01/backend/marketplace.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Add approval_status column
    cursor.execute("ALTER TABLE products ADD COLUMN approval_status TEXT DEFAULT 'pending';")
    print("Column 'approval_status' added to 'products' table.")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("Column 'approval_status' already exists.")
    else:
        print(f"Error adding approval_status: {e}")

try:
    # Add rejection_reason column
    cursor.execute("ALTER TABLE products ADD COLUMN rejection_reason TEXT;")
    print("Column 'rejection_reason' added to 'products' table.")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("Column 'rejection_reason' already exists.")
    else:
        print(f"Error adding rejection_reason: {e}")

try:
    # Add approved_at column
    cursor.execute("ALTER TABLE products ADD COLUMN approved_at TIMESTAMP;")
    print("Column 'approved_at' added to 'products' table.")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("Column 'approved_at' already exists.")
    else:
        print(f"Error adding approved_at: {e}")

try:
    # Add approved_by column
    cursor.execute("ALTER TABLE products ADD COLUMN approved_by INTEGER;")
    print("Column 'approved_by' added to 'products' table.")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("Column 'approved_by' already exists.")
    else:
        print(f"Error adding approved_by: {e}")

try:
    # Update existing products to be approved (so they don't disappear)
    cursor.execute("UPDATE products SET approval_status = 'approved' WHERE approval_status IS NULL OR approval_status = '';")
    print(f"Updated {cursor.rowcount} existing products to 'approved' status.")
except Exception as e:
    print(f"Error updating existing products: {e}")

finally:
    conn.commit()
    conn.close()
    print("Migration completed!")
