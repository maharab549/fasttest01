#!/usr/bin/env python3
"""
Test script to create a new product with an image via the API.
This tests the complete flow: create product -> upload image.
"""

import requests
import json
from io import BytesIO
from PIL import Image
import time

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 70)
print("Testing Product Creation with Image Upload")
print("=" * 70)

# Step 1: Register a new seller
seller_email = f"test_seller_{int(time.time())}@example.com"
seller_data = {
    "email": seller_email,
    "password": "test123456",
    "full_name": "Test Seller",
    "is_seller": True
}

print(f"\n1. Registering seller: {seller_email}")
try:
    resp = requests.post(f"{BASE_URL}/auth/register", json=seller_data, timeout=5)
    print(f"   Status: {resp.status_code}")
    if resp.status_code != 201 and resp.status_code != 200:
        print(f"   Response: {resp.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

# Step 2: Login to get token
print(f"\n2. Logging in seller...")
login_data = {"email": seller_email, "password": "test123456"}
try:
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=5)
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        print(f"   ✅ Login successful, got token")
    else:
        print(f"   ❌ Login failed: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
        exit(1)
except Exception as e:
    print(f"   Error: {e}")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

# Step 3: Create a new product
print(f"\n3. Creating a new product...")
product_data = {
    "title": "Test Product with Image",
    "description": "This is a test product created to verify image upload during product creation",
    "short_description": "Test product",
    "price": 99.99,
    "compare_price": 119.99,
    "sku": f"SKU-TEST-{int(time.time())}",
    "inventory_count": 100,
    "category_id": 1,
}

try:
    resp = requests.post(f"{BASE_URL}/products/", json=product_data, headers=headers, timeout=5)
    if resp.status_code in [200, 201]:
        product = resp.json()
        product_id = product.get("id")
        print(f"   ✅ Product created: ID={product_id}")
        print(f"   Title: {product.get('title')}")
        print(f"   Images: {product.get('images', [])}")
    else:
        print(f"   ❌ Failed: {resp.status_code}")
        print(f"   Response: {resp.text[:300]}")
        exit(1)
except Exception as e:
    print(f"   Error: {e}")
    exit(1)

# Step 4: Create and upload a test image
print(f"\n4. Creating and uploading test image...")
try:
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    files = {'file': ('test_image.png', img_bytes, 'image/png')}
    params = {'product_id': product_id}
    
    resp = requests.post(
        f"{BASE_URL}/products/upload-image",
        files=files,
        params=params,
        headers=headers,
        timeout=10
    )
    
    if resp.status_code in [200, 201]:
        image_data = resp.json()
        print(f"   ✅ Image uploaded successfully")
        print(f"   Image ID: {image_data.get('id')}")
        print(f"   Image URL: {image_data.get('image_url')}")
    else:
        print(f"   ❌ Upload failed: {resp.status_code}")
        print(f"   Response: {resp.text[:300]}")
except Exception as e:
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Fetch the product to see if image is there
print(f"\n5. Fetching product to verify image...")
try:
    resp = requests.get(f"{BASE_URL}/products/{product_id}", headers=headers, timeout=5)
    if resp.status_code == 200:
        product = resp.json()
        images = product.get('images', [])
        print(f"   Product images: {images}")
        if images and len(images) > 0:
            print(f"   ✅ Image found! First image URL: {images[0]}")
        else:
            print(f"   ❌ No images found for product")
    else:
        print(f"   ❌ Failed to fetch: {resp.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# Step 6: Fetch from product list to verify
print(f"\n6. Fetching product from list to verify image...")
try:
    resp = requests.get(f"{BASE_URL}/products/?page=1", timeout=5)
    if resp.status_code == 200:
        products = resp.json()
        # Find our product in the list
        our_product = None
        for p in products:
            if p.get('id') == product_id:
                our_product = p
                break
        
        if our_product:
            images = our_product.get('images', [])
            print(f"   Product found in list")
            print(f"   Images in list response: {images}")
            if images and len(images) > 0:
                print(f"   ✅ Image visible in list! First image URL: {images[0]}")
            else:
                print(f"   ⚠️  Image not in list response")
        else:
            print(f"   ⚠️  Product not found in first page of list")
    else:
        print(f"   ❌ Failed: {resp.status_code}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 70)
print("Test completed!")
print("=" * 70)
