import requests
import json

print("Testing Backend API...")
print("=" * 60)

try:
    # Test 1: Get all products
    response = requests.get("http://127.0.0.1:8000/api/v1/products/?skip=0&limit=5")
    print(f"✅ GET /api/v1/products/ - Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total: {len(data) if isinstance(data, list) else 'N/A'} products")
        if isinstance(data, list) and len(data) > 0:
            print(f"   First product: {data[0].get('name', 'N/A')}")
    else:
        print(f"   Error: {response.text[:200]}")
    
    print()
    
    # Test 2: Get featured products
    response = requests.get("http://127.0.0.1:8000/api/v1/products/featured")
    print(f"✅ GET /api/v1/products/featured - Status: {response.status_code}")
    
    print()
    
    # Test 3: Health check
    response = requests.get("http://127.0.0.1:8000/api/v1/admin/health/status")
    print(f"✅ GET /api/v1/admin/health/status - Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Data: {response.json()}")

except Exception as e:
    print(f"❌ Error: {e}")

print("=" * 60)
