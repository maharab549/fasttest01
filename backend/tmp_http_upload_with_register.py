import requests
import io
import time

# Wait briefly for server to come up
print('Sleeping 1s to let server start...')
time.sleep(1)

base = "http://127.0.0.1:8000/api/v1"
username = 'test_seller'
password = 'password123'
email = 'test_seller@example.com'

# Step 1: Register the user if needed
print('Attempting to register seller...')
register_url = f"{base}/auth/register"
register_resp = requests.post(register_url, json={
    "username": username,
    "email": email,
    "full_name": "Test Seller",
    "password": password,
    "is_seller": True
})
print(f'Register status: {register_resp.status_code}')
if register_resp.status_code in [200, 201]:
    print('User registered successfully')
elif register_resp.status_code == 400:
    print('User already exists (expected)')
else:
    print(f'Register error: {register_resp.text[:200]}')

# Step 2: Login to get token
print('Logging in...')
login_url = f"{base}/auth/login"
login_resp = requests.post(login_url, json={"username": username, "password": password})
print(f'Login status: {login_resp.status_code}')
try:
    token = login_resp.json().get('access_token')
    print(f'Token obtained: {token[:40]}...')
except Exception as e:
    print(f'Login error: {login_resp.text[:200]}')
    token = None

if not token:
    print('No token obtained; aborting')
    raise SystemExit(1)

# Step 3: Upload image
headers = {"Authorization": f"Bearer {token}"}
fake_image = io.BytesIO(b"\xff\xd8\xff\xdb" + b"0"*1024 + b"\xff\xd9")
files = {"file": ("test_upload.jpg", fake_image, "image/jpeg")}

upload_url = f"{base}/products/upload-image"
params = {"product_id": 3}
print(f'Uploading to {upload_url}?product_id=3')
resp = requests.post(upload_url, files=files, params=params, headers=headers)
print(f'Upload status: {resp.status_code}')
try:
    print(f'Upload response: {resp.json()}')
except Exception as e:
    print(f'Upload response (text): {resp.text[:500]}')

print('Done!')
