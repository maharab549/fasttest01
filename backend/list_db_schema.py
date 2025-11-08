import sqlite3

DB_PATH = "app/database.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("\n=== ALL TABLES IN DATABASE ===\n")
for table in tables:
    table_name = table[0]
    print(f"✓ {table_name}")

print("\n=== LOYALTY RELATED TABLES ===\n")

# Get columns of loyalty tables
for table in tables:
    table_name = table[0]
    if 'loyalty' in table_name.lower() or 'reward' in table_name.lower() or 'redemption' in table_name.lower():
        print(f"\n📋 {table_name}:")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            col_name, col_type = col[1], col[2]
            print(f"   - {col_name}: {col_type}")

conn.close()
