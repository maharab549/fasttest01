#!/usr/bin/env python
"""Test withdrawal endpoint"""

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app import crud, schemas
from sqlalchemy.orm import Session

# Initialize DB
Base.metadata.create_all(bind=engine)

client = TestClient(app)
db = SessionLocal()

# Register and login a seller
register_response = client.post("/api/v1/auth/register", json={
    "email": "seller_test@example.com",
    "password": "password123",
    "full_name": "Test Seller"
})

print(f"Register Status: {register_response.status_code}")
print(f"Register Response: {register_response.json()}")

# Make seller
seller_user = db.query(crud.models.User).filter(crud.models.User.email == "seller_test@example.com").first()
if seller_user:
    seller_user.is_seller = True
    db.commit()

# Login
login_response = client.post("/api/v1/auth/login", json={
    "email": "seller_test@example.com",
    "password": "password123"
})

print(f"\nLogin Status: {login_response.status_code}")
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# First, create a seller record if needed
seller = crud.get_seller_by_user_id(db, seller_user.id)
if not seller:
    seller = crud.models.Seller(user_id=seller_user.id, store_name="Test Store")
    db.add(seller)
    db.commit()
    db.refresh(seller)

# Add some revenue by creating test orders
from app.models import Product, Category, Order, OrderItem
cat = Category(name="Test")
db.add(cat)
db.commit()

product = Product(
    seller_id=seller.id,
    category_id=cat.id,
    title="Test Product",
    price=100.0,
    inventory_count=10
)
db.add(product)
db.commit()

# Create an order
order = Order(
    user_id=seller_user.id,
    status="completed",
    total_amount=100.0,
    order_number="TEST001"
)
db.add(order)
db.commit()

# Add order item
order_item = OrderItem(
    order_id=order.id,
    product_id=product.id,
    quantity=1,
    price=100.0,
    total_price=100.0
)
db.add(order_item)
db.commit()

# Check dashboard stats
dashboard_response = client.get("/api/v1/seller/dashboard", headers=headers)
print(f"\nDashboard Status: {dashboard_response.status_code}")
dashboard_data = dashboard_response.json()
print(f"Dashboard Balance: {dashboard_data.get('balance')}")
print(f"Dashboard Total Revenue: {dashboard_data.get('total_revenue')}")

# Set payout info
payout_response = client.put("/api/v1/seller/payout-info", headers=headers, json={
    "method_type": "bank_transfer",
    "bank_account": "1234567890",
    "bank_code": "123456",
    "account_holder_name": "Test"
})
print(f"\nPayout Info Status: {payout_response.status_code}")
print(f"Payout Info: {payout_response.json()}")

# Try to withdraw
withdraw_response = client.post("/api/v1/seller/withdraw", headers=headers, json={
    "amount": 50.0
})

print(f"\nWithdraw Status: {withdraw_response.status_code}")
print(f"Withdraw Response: {withdraw_response.json()}")

if withdraw_response.status_code != 200:
    print(f"\nERROR: Withdrawal failed!")
    print(f"Full response: {withdraw_response.text}")
