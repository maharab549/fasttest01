#!/usr/bin/env python
"""Test the payout-info endpoints with a valid token"""

import requests
from jose import jwt
from datetime import datetime, timedelta
from app.config import settings

# Create a test token for techstore
payload = {
    "sub": "techstore",
    "exp": datetime.utcnow() + timedelta(hours=1)
}

token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
headers = {"Authorization": f"Bearer {token}"}

print("=== TESTING WITH VALID TOKEN ===\n")
print(f"Token: {token[:50]}...\n")

# Test GET
print("1. Testing GET /api/v1/seller/payout-info...")
get_response = requests.get("http://127.0.0.1:8000/api/v1/seller/payout-info", headers=headers)
print(f"   Status Code: {get_response.status_code}")
print(f"   Headers: {dict(get_response.headers)}")
print(f"   Response: {get_response.text[:200]}")
print()

# Test PUT
print("2. Testing PUT /api/v1/seller/payout-info...")
put_data = {
    "method_type": "bank_transfer",
    "account_holder_name": "Test Seller",
    "bank_account": "DE89370400440532013000",
    "bank_code": "MARKDEFF"
}
put_response = requests.put("http://127.0.0.1:8000/api/v1/seller/payout-info", json=put_data, headers=headers)
print(f"   Status Code: {put_response.status_code}")
print(f"   Response: {put_response.text[:200]}")
