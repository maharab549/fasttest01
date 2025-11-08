#!/usr/bin/env python
"""Create a test token and test the endpoint"""

from jose import jwt
from datetime import datetime, timedelta
from app.config import settings

# Create a test token for techstore
payload = {
    "sub": "techstore",
    "exp": datetime.utcnow() + timedelta(hours=1)
}

token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
print(f"Test Token:\n{token}\n")
print(f"Use this token with:")
print(f'curl -H "Authorization: Bearer {token}" http://127.0.0.1:8000/api/v1/seller/payout-info')
