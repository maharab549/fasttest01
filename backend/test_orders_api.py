"""
Test the orders API endpoint directly
"""

import requests
import json
from pathlib import Path

def test_orders_api():
    """Test the /orders endpoint"""
    
    # Backend URL
    BASE_URL = "http://localhost:8000/api/v1"
    
    # First, let's get a test token
    print("🔐 Getting test token...")
    
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "customer1@marketplace.com",
            "password": "password123"
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    login_data = login_response.json()
    token = login_data.get('access_token')
    user = login_data.get('user')
    
    print(f"✅ Logged in as user: {user}")
    print(f"   Token: {token[:20]}...")
    
    # Now test orders endpoint
    print("\n📦 Testing /orders endpoint...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    orders_response = requests.get(
        f"{BASE_URL}/orders/",
        headers=headers
    )
    
    print(f"Status: {orders_response.status_code}")
    print(f"Headers: {dict(orders_response.headers)}")
    
    try:
        data = orders_response.json()
        print(f"\n✅ Response received!")
        print(f"Type: {type(data)}")
        
        if isinstance(data, list):
            print(f"Orders count: {len(data)}")
            if len(data) > 0:
                print(f"\nFirst order structure:")
                print(json.dumps(data[0], indent=2, default=str))
        else:
            print(f"Response structure:")
            print(json.dumps(data, indent=2, default=str))
            
    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        print(f"Raw text: {orders_response.text[:500]}")

if __name__ == "__main__":
    print("🧪 Testing Orders API...\n")
    test_orders_api()
