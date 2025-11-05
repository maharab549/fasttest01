import requests
import json

url = "http://localhost:8000/api/v1/products/slug/smartphone-128gb"
print(f"Testing: {url}\n")

response = requests.get(url)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"✅ Product: {data.get('title')}")
    print(f"📦 Has variants: {data.get('has_variants')}")
    print(f"📊 Variants count: {len(data.get('variants', []))}")
    print()
    
    if data.get('variants'):
        print("Variants:")
        for v in data.get('variants', []):
            print(f"  - {v.get('variant_name')} | +${v.get('price_adjustment'):.2f} | Stock: {v.get('inventory_count')}")
    else:
        print("❌ No variants in response!")
        print(f"Response keys: {list(data.keys())}")
else:
    print(f"Error: {response.text}")
