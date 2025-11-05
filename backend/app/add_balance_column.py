import sqlite3

DB_PATH = 'D:/All github project/fasttest01/backend/marketplace.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE sellers ADD COLUMN balance REAL DEFAULT 0.0;")
    print("Column 'balance' added to 'sellers' table.")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("Column 'balance' already exists.")
    else:
        print(f"Error: {e}")
finally:
    conn.commit()
    conn.close()
