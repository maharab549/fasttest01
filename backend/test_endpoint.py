import urllib.request
import json

try:
    url = "http://localhost:8000/api/v1/products/2"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode())
    print("✅ SUCCESS! Got product data:")
    print(f"ID: {data.get('id')}")
    print(f"Title: {data.get('title')}")
    print(f"Price: {data.get('price')}")
    print(f"Description: {str(data.get('description', ''))[:100]}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
