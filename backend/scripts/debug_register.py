import sys
from pathlib import Path
# Make sure project root is on path
proj_root = Path(__file__).resolve().parents[1]
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
resp = client.post("/api/auth/register", json={
    "email": "newuser@example.com",
    "username": "newuser",
    "full_name": "New User",
    "password": "newpassword123"
})
print("status", resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)
