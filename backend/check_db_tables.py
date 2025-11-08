import sqlite3

DB_PATH = "app/database.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("\n=== DATABASE TABLES ===\n")
for table in tables:
    print(f"- {table[0]}")

# Check if redemptions table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='redemptions'")
if cursor.fetchone():
    print("\n✓ Redemptions table exists!")
    
    # Check the code
    cursor.execute("""
        SELECT id, loyalty_account_id, reward_code, reward_value, status, 
               order_id, used_at
        FROM redemptions
        WHERE reward_code = 'DISC-EAAE2CA9'
    """)
    
    result = cursor.fetchone()
    if result:
        print("\n✓ Code DISC-EAAE2CA9 found!")
        print(f"  ID: {result[0]}")
        print(f"  Status: {result[4]}")
        print(f"  Order ID: {result[5]}")
        print(f"  Used At: {result[6]}")
    else:
        print("\n✗ Code DISC-EAAE2CA9 NOT found!")
else:
    print("\n✗ Redemptions table DOES NOT exist!")

conn.close()
