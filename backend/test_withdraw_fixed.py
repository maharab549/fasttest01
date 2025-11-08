#!/usr/bin/env python
"""Test withdrawal endpoint"""

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app import crud

# Initialize DB
Base.metadata.create_all(bind=engine)

client = TestClient(app)
db = SessionLocal()

# Register and login a seller
register_response = client.post("/api/v1/auth/register", json={
    "email": "seller_withdraw@example.com",
    "password": "password123",
    "full_name": "Test Seller",
    "username": "seller_withdraw"
})

print(f"1. Register Status: {register_response.status_code}")

# Make seller
seller_user = db.query(crud.models.User).filter(crud.models.User.email == "seller_withdraw@example.com").first()
if seller_user:
    seller_user.is_seller = True
    db.commit()

# Login
login_response = client.post("/api/v1/auth/login", json={
    "email": "seller_withdraw@example.com",
    "password": "password123"
})

print(f"2. Login Status: {login_response.status_code}")
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create seller record
seller = crud.get_seller_by_user_id(db, seller_user.id)
if not seller:
    seller = crud.models.Seller(user_id=seller_user.id, store_name="Test Store")
    db.add(seller)
    db.commit()
    db.refresh(seller)

# Add payout info
payout_response = client.put("/api/v1/seller/payout-info", headers=headers, json={
    "method_type": "bank_transfer",
    "bank_account": "1234567890",
    "bank_code": "123456",
    "account_holder_name": "Test"
})
print(f"3. Payout Info Status: {payout_response.status_code}")

# Try to withdraw
withdraw_response = client.post("/api/v1/seller/withdraw", headers=headers, json={
    "amount": 50.0
})

print(f"4. Withdraw Status: {withdraw_response.status_code}")
if withdraw_response.status_code == 200:
    print(f"✅ SUCCESS! Withdrawal response: {withdraw_response.json()}")
else:
    print(f"❌ FAILED! Response: {withdraw_response.json()}")
