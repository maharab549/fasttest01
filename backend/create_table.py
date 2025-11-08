import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create product_variants table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS product_variants (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    sku TEXT UNIQUE,
    variant_name TEXT,
    color TEXT,
    size TEXT,
    material TEXT,
    style TEXT,
    storage TEXT,
    ram TEXT,
    other_attributes TEXT,
    price_adjustment REAL DEFAULT 0,
    inventory_count INTEGER DEFAULT 0,
    images TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id)
)''')

conn.commit()
print("OK")
conn.close()
