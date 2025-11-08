import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Create product_images table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS product_images (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    alt_text VARCHAR(255),
    is_primary BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, image_url),
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
)''')

# Create indexes
c.execute('''CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images(product_id)''')

conn.commit()
print("OK")
conn.close()
