#!/usr/bin/env python3
"""Test seller returns endpoint"""
import requests

# Test with the bookworm seller account
seller_username = "bookworm"
seller_password = "seller123"

base_url = "http://localhost:8000/api/v1"

def main():
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
        try:
            print(login_response.json())
        except Exception:
            print(login_response.text)
        return 1

    token = login_response.json().get("access_token")
    print(f"✅ Logged in successfully! Token: {token[:20]}..." if token else "✅ Logged in (no token returned)")

    # Get seller returns
    print(f"\n2. Fetching seller returns...")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
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
            print(f"  - Return #{ret.get('return_number')} (Order: {ret.get('order_id')})")
    else:
        print(f"❌ Error fetching returns")
        try:
            print(returns_response.json())
        except Exception:
            print(returns_response.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
