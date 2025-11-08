#!/usr/bin/env python
"""Test the endpoints using TestClient"""

from fastapi.testclient import TestClient
from app.main import app
from jose import jwt
from datetime import datetime, timedelta
from app.config import settings

# Create test client
client = TestClient(app)

# Create a test token for techstore
payload = {
    "sub": "techstore",
    "exp": datetime.utcnow() + timedelta(hours=1)
}

token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

print("=== TESTING WITH TESTCLIENT ===\n")
print(f"Token: {token[:50]}...\n")

# Test GET
print("1. Testing GET /api/v1/seller/payout-info...")
headers = {"Authorization": f"Bearer {token}"}
resp = client.get("/api/v1/seller/payout-info", headers=headers)
print(f"   Status Code: {resp.status_code}")
print(f"   Response: {resp.json()}")
print()

# Test PUT
print("2. Testing PUT /api/v1/seller/payout-info...")
put_data = {
    "method_type": "bank_transfer",
    "account_holder_name": "Test Seller",
    "bank_account": "DE89370400440532013000",
    "bank_code": "MARKDEFF"
}
resp = client.put("/api/v1/seller/payout-info", json=put_data, headers=headers)
print(f"   Status Code: {resp.status_code}")
print(f"   Response: {resp.json()}")
