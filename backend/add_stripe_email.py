#!/usr/bin/env python
"""Add missing stripe_email column to sellers table"""

from app.database import engine
from sqlalchemy import text

def add_stripe_email_column():
    """Add stripe_email column if it doesn't exist"""
    with engine.connect() as conn:
        # Check if column exists
        cursor = conn.connection.cursor()
        cursor.execute("PRAGMA table_info(sellers)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'stripe_email' not in columns:
            print("Adding stripe_email column to sellers table...")
            conn.execute(text("ALTER TABLE sellers ADD COLUMN stripe_email VARCHAR"))
            conn.commit()
            print("✓ stripe_email column added successfully")
        else:
            print("✓ stripe_email column already exists")

if __name__ == "__main__":
    add_stripe_email_column()
