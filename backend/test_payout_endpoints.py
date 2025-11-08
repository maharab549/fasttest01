#!/usr/bin/env python
"""Test the payout-info endpoint directly"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# First, login to get a token
print("=== TESTING PAYOUT-INFO ENDPOINT ===\n")

# Try login with a test seller account
login_data = {
    "username": "techstore",
    "password": "techstore123"
}

print("1. Attempting login...")
login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
print(f"   Status: {login_response.status_code}")

if login_response.status_code == 200:
    token = login_response.json().get("access_token")
    print(f"   Token: {token[:30]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test GET payout-info
    print("\n2. Testing GET /api/v1/seller/payout-info...")
    get_response = requests.get(
        f"{BASE_URL}/api/v1/seller/payout-info",
        headers=headers
    )
    print(f"   Status: {get_response.status_code}")
    print(f"   Response: {get_response.json()}")
    
    # Test PUT payout-info
    print("\n3. Testing PUT /api/v1/seller/payout-info...")
    put_data = {
        "method_type": "bank_transfer",
        "account_holder_name": "Test Seller",
        "bank_account": "DE89370400440532013000",
        "bank_code": "MARKDEFF",
        "bank_name": "Deutsche Bank"
    }
    put_response = requests.put(
        f"{BASE_URL}/api/v1/seller/payout-info",
        json=put_data,
        headers=headers
    )
    print(f"   Status: {put_response.status_code}")
    print(f"   Response: {put_response.json()}")
else:
    print(f"   ERROR: Login failed - {login_response.text}")
