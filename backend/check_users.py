#!/usr/bin/env python
"""Get existing users from the database"""

from app.database import SessionLocal
from app.models import User

db = SessionLocal()

try:
    users = db.query(User).all()
    print("=== USERS IN DATABASE ===\n")
    for user in users:
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Is Seller: {user.is_seller}")
        print(f"Is Admin: {user.is_admin}")
        print(f"Active: {user.is_active}")
        print("-" * 40)
finally:
    db.close()
