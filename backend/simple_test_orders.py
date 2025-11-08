"""
Simple test to verify orders endpoint works
"""

import subprocess
import time
import requests
import json

def start_backend():
    """Start backend in background"""
    cmd = r'cd "d:\All github project\fasttest01\backend" ; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)  # Wait for server to start
    return process

def test_orders_endpoint():
    """Test orders endpoint"""
    
    BASE_URL = "http://localhost:8000/api/v1"
    
    print("🧪 Testing Orders API\n")
    
    # Login
    print("1️⃣  Logging in...")
    try:
        login_resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": "customer1@marketplace.com", "password": "password123"},
            timeout=5
        )
        
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.status_code}")
            print(login_resp.text[:200])
            return
        
        data = login_resp.json()
        token = data.get('access_token')
        user_id = data.get('user', {}).get('id')
        
        print(f"✅ Logged in as user {user_id}")
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Get orders
    print("\n2️⃣  Fetching orders...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        orders_resp = requests.get(
            f"{BASE_URL}/orders/?limit=50",
            headers=headers,
            timeout=5
        )
        
        print(f"Status: {orders_resp.status_code}")
        
        if orders_resp.status_code == 200:
            orders = orders_resp.json()
            print(f"✅ Got response!")
            print(f"Type: {type(orders)}")
            
            if isinstance(orders, list):
                print(f"✅ Response is an array")
                print(f"Orders count: {len(orders)}")
                
                if len(orders) > 0:
                    print(f"\n📋 First order:")
                    print(json.dumps(orders[0], indent=2, default=str)[:500])
                else:
                    print("⚠️  No orders found for this user")
            else:
                print(f"⚠️  Response is not an array:")
                print(json.dumps(orders, indent=2, default=str)[:500])
        else:
            print(f"❌ Failed: {orders_resp.status_code}")
            print(f"Error: {orders_resp.text[:300]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting backend...\n")
    process = start_backend()
    
    try:
        test_orders_endpoint()
    finally:
        print("\n\n🛑 Stopping backend...")
        process.terminate()
        process.wait()
