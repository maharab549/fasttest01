#!/usr/bin/env python
"""Test what happens during route matching"""

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_seller
from app import crud, schemas, auth

# Create a simple test router to isolate the issue
from fastapi import APIRouter

test_router = APIRouter(prefix="/test", tags=["test"])

@test_router.get("/payout-info")
def test_get(db: Session = Depends(get_db)):
    return {"method": "GET"}

@test_router.put("/payout-info")
def test_put(data: dict, db: Session = Depends(get_db)):
    return {"method": "PUT"}

# Create test app
test_app = FastAPI()
test_app.include_router(test_router, prefix="/api/v1")

# Test it
client = TestClient(test_app)

print("Testing simple GET...")
resp = client.get("/api/v1/test/payout-info")
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}")

print("\nTesting simple PUT...")
resp = client.put("/api/v1/test/payout-info", json={"test": "data"})
print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}")
