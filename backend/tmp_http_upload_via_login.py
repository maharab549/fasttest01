import requests
import io
import time

# Wait briefly for server to come up
print('Sleeping 1s to let server start...')
time.sleep(1)

base = "http://127.0.0.1:8000/api/v1"
username = 'test_seller'
password = 'password123'

# Login to get token
login_url = f"{base}/auth/login"
print('Logging in to', login_url)
resp = requests.post(login_url, json={"username": username, "password": password})
print('Login status:', resp.status_code)
try:
    token = resp.json().get('access_token')
except Exception:
    print('Login response:', resp.text)
    token = None

if not token:
    print('No token obtained; aborting')
    raise SystemExit(1)

headers = {"Authorization": f"Bearer {token}"}

# prepare file
fake_image = io.BytesIO(b"\xff\xd8\xff\xdb" + b"0"*1024 + b"\xff\xd9")
files = {"file": ("test_upload.jpg", fake_image, "image/jpeg")}

upload_url = f"{base}/products/upload-image"
params = {"product_id": 3}
print('Uploading to', upload_url, 'params', params)
resp2 = requests.post(upload_url, files=files, params=params, headers=headers)
print('Upload status:', resp2.status_code)
try:
    print('Upload JSON:', resp2.json())
except Exception:
    print('Upload text:', resp2.text[:1000])

# Done
