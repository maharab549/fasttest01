#!/usr/bin/env python3
"""Test seller returns endpoint"""
import requests

# Test with the bookworm seller account
seller_username = "bookworm"
seller_password = "seller123"

base_url = "http://localhost:8000/api/v1"

# Login as seller
print(f"\n1. Logging in as {seller_username}...")
login_response = requests.post(
    f"{base_url}/auth/login",
    data={
        "username": seller_username,
        "password": seller_password
    }
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.json())
    exit(1)

token = login_response.json()["access_token"]
print(f"✅ Logged in successfully! Token: {token[:20]}...")

# Get seller returns
print(f"\n2. Fetching seller returns...")
headers = {"Authorization": f"Bearer {token}"}
returns_response = requests.get(
    f"{base_url}/returns/seller/returns",
    headers=headers
)

print(f"Status Code: {returns_response.status_code}")
print(f"Response: {returns_response.text}")

if returns_response.status_code == 200:
    returns = returns_response.json()
    print(f"\n✅ Found {len(returns)} returns")
    for ret in returns:
        print(f"  - Return #{ret['return_number']} (Order: {ret['order_id']})")
else:
    print(f"❌ Error fetching returns")
    print(returns_response.json())
