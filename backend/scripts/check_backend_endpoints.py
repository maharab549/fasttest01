"""
Quick health-check script:
- Registers a new user
- Logs in
- Fetches /api/products

Run while the server is running locally on http://127.0.0.1:8000
"""
import sys
import time
import json

import requests

BASE = "http://127.0.0.1:8000/api"

session = requests.Session()

print("Checking backend endpoints at", BASE)

# 1) Register a test user (ignore if already exists)
reg_payload = {
    "email": "checkuser@example.com",
    "username": "checkuser",
    "full_name": "Check User",
    "password": "checkpassword123"
}
try:
    r = session.post(f"{BASE}/auth/register", json=reg_payload, timeout=5)
    print("REGISTER status:", r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text[:400])
except Exception as e:
    print("REGISTER failed:", e)

# 2) Login
login_payload = {"username": reg_payload["email"], "password": reg_payload["password"]}
try:
    r = session.post(f"{BASE}/auth/login", data=login_payload, timeout=5)
    print("LOGIN status:", r.status_code)
    try:
        login_json = r.json()
        print(json.dumps(login_json, indent=2))
    except Exception:
        print(r.text[:400])
        login_json = {}
except Exception as e:
    print("LOGIN failed:", e)
    login_json = {}

token = login_json.get("access_token")
headers = {"Authorization": f"Bearer {token}"} if token else {}

# 3) Get products
try:
    r = session.get(f"{BASE}/products", headers=headers, timeout=5)
    print("GET /products status:", r.status_code)
    # print truncated body
    try:
        body = r.json()
        print("Products response (truncated):", json.dumps(body, indent=2)[:1000])
    except Exception:
        print(r.text[:1000])
except Exception as e:
    print("GET /products failed:", e)

# 4) Check auth/me if token present
if token:
    try:
        r = session.get(f"{BASE}/auth/me", headers=headers, timeout=5)
        print("GET /auth/me status:", r.status_code)
        try:
            print(json.dumps(r.json(), indent=2))
        except Exception:
            print(r.text[:400])
    except Exception as e:
        print("GET /auth/me failed:", e)

print("Done.")
