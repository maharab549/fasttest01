#!/usr/bin/env python3
"""
Test script to verify all product list endpoints return image URLs (not IDs).
This checks that the response validation errors have been fixed.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def check_response_images(endpoint, response_data):
    """Verify that images in response are URLs (strings), not IDs (integers)"""
    errors = []
    
    if isinstance(response_data, list):
        products = response_data
    elif isinstance(response_data, dict) and "data" in response_data:
        products = response_data.get("data", [])
    else:
        return errors
    
    for i, product in enumerate(products):
        if "images" in product and product["images"]:
            for j, image in enumerate(product["images"]):
                if isinstance(image, int):
                    errors.append(f"  Product {i}: images[{j}] is integer {image} (should be URL string)")
                elif not isinstance(image, str):
                    errors.append(f"  Product {i}: images[{j}] is {type(image).__name__} (should be string)")
    
    return errors

print("=" * 70)
print("Testing Image URL Conversion in All Endpoints")
print("=" * 70)

# Register a test seller if needed
test_email = "test_seller_urls@example.com"
test_user = {
    "email": test_email,
    "password": "test123456",
    "full_name": "Test Seller URLs",
    "is_seller": True
}

# Try to register (ignore if already exists)
try:
    resp = requests.post(f"{BASE_URL}/auth/register", json=test_user, timeout=5)
except:
    pass

# Login to get token
login_data = {"email": test_email, "password": "test123456"}
try:
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=5)
    if resp.status_code == 200:
        token = resp.json().get("access_token")
    else:
        token = None
except:
    token = None

headers = {"Authorization": f"Bearer {token}"} if token else {}

# Test endpoints
endpoints = [
    ("GET /api/v1/products/ (main list)", f"{BASE_URL}/products/", "GET", None),
    ("GET /api/v1/products/featured (featured)", f"{BASE_URL}/products/featured", "GET", None),
    ("GET /api/v1/products/search (search)", f"{BASE_URL}/products/search?q=test", "GET", None),
    ("GET /api/v1/categories/1/products (category)", f"{BASE_URL}/categories/1/products", "GET", None),
]

if token:
    endpoints.extend([
        ("GET /api/v1/seller/products (seller products)", f"{BASE_URL}/seller/products", "GET", headers),
    ])

print()
all_good = True

for endpoint_name, url, method, hdrs in endpoints:
    print(f"\n{endpoint_name}")
    print("-" * 70)
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=hdrs or {}, timeout=5)
        else:
            resp = requests.post(url, json={}, headers=hdrs or {}, timeout=5)
        
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            errors = check_response_images(endpoint_name, data)
            
            if errors:
                print(f"❌ FAILED - Images contain non-string values:")
                for error in errors[:5]:  # Show first 5 errors
                    print(error)
                if len(errors) > 5:
                    print(f"  ... and {len(errors) - 5} more errors")
                all_good = False
            else:
                # Check if there are any products
                if isinstance(data, list):
                    count = len(data)
                else:
                    count = len(data.get("data", []))
                
                if count > 0:
                    print(f"✅ PASSED - All images are valid strings ({count} products)")
                else:
                    print(f"⚠️  NO PRODUCTS - Endpoint returned empty list")
        else:
            print(f"⚠️  Error response: {resp.status_code}")
            print(f"   {resp.text[:200]}")
    
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        all_good = False

print("\n" + "=" * 70)
if all_good:
    print("✅ All tests PASSED!")
else:
    print("❌ Some tests FAILED - Check output above")
print("=" * 70)
