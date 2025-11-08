import requests
import json

BASE_URL = 'http://localhost:8000'

# Test data
test_email = 'customer1@marketplace.com'
test_password = 'password123'
discount_code = 'WELCOME20'

print('=== DISCOUNT CODE TEST ===\n')

# Step 1: Login
print('Step 1: Login')
response = requests.post(f'{BASE_URL}/api/v1/auth/login', json={
    'email': test_email,
    'password': test_password
})
if response.status_code == 200:
    data = response.json()
    token = data['access_token']
    user_id = data['user']['id']
    print(f'✅ Logged in: User {user_id}, Token: {token[:20]}...')
else:
    print(f'❌ Login failed: {response.status_code}')
    print(response.text)
    exit(1)

# Step 2: Validate discount code
print(f'\nStep 2: Validate discount code "{discount_code}"')
response = requests.post(
    f'{BASE_URL}/api/v1/orders/validate-discount',
    params={'code': discount_code},
    headers={'Authorization': f'Bearer {token}'}
)
print(f'Status: {response.status_code}')
print(f'Response: {json.dumps(response.json(), indent=2)}')
