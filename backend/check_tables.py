import sqlite3

conn = sqlite3.connect('app/database.db')
cursor = conn.cursor()

# Check all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("=" * 60)
print("TABLES IN DATABASE")
print("=" * 60)
for table in tables:
    print(f"  - {table[0]}")
    cursor.execute(f"PRAGMA table_info({table[0]});")
    cols = cursor.fetchall()
    for col in cols:
        print(f"    → {col[1]} ({col[2]})")
    print()

conn.close()
