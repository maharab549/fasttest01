from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('Calling GET /api/v1/products/')
# Use Host header 'localhost' to satisfy TrustedHostMiddleware
resp = client.get('/api/v1/products/', headers={'host': 'localhost'})
print('Status code:', resp.status_code)
try:
    print('Response JSON keys:', list(resp.json().keys()))
except Exception as e:
    print('Response content:', resp.text)

print('\nCalling POST /api/v1/auth/login with customer1 credentials')
# Use Host header 'localhost' to satisfy TrustedHostMiddleware
login_payload = {"username": "customer1", "password": "customer123"}
resp = client.post('/api/v1/auth/login', json=login_payload, headers={'host': 'localhost'})
print('Status code:', resp.status_code)
try:
    print('Login response JSON:', resp.json())
except Exception as e:
    print('Login response content:', resp.text)

# If login succeeded, try to call protected endpoint /auth/me
if resp.status_code == 200:
    token = resp.json().get('access_token')
    # Include Host header to satisfy TrustedHostMiddleware
    headers = {'Authorization': f'Bearer {token}', 'host': 'localhost'}
    print('\nCalling GET /api/v1/auth/me')
    me_resp = client.get('/api/v1/auth/me', headers=headers)
    print('Status code:', me_resp.status_code)
    print('Response:', me_resp.json())
else:
    print('\nLogin failed; skipping /auth/me')
