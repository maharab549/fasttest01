import sqlite3

DB_PATH = "app/database.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get list of all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check loyalty_accounts schema
print("\nLoyalty Accounts schema:")
cursor.execute("PRAGMA table_info(loyalty_accounts)")
for row in cursor.fetchall():
    print(f"  {row}")

# Check redemptions schema
print("\nRedemptions schema:")
cursor.execute("PRAGMA table_info(redemptions)")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
