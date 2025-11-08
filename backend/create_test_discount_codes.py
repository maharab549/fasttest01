#!/usr/bin/env python
"""
Script to create test discount codes for testing the checkout discount flow
"""

from app.main import app
from app.database import SessionLocal, Base, engine
from app import models, crud, schemas
from datetime import datetime, timedelta
import json

# Ensure tables exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    print("=" * 80)
    print("CREATING TEST DISCOUNT CODES")
    print("=" * 80)

    # Get test user
    test_user = db.query(models.User).filter(
        models.User.email == "customer1@marketplace.com"
    ).first()

    if not test_user:
        print("❌ Test user customer1@marketplace.com not found")
        print("Please create this user first via registration")
        exit(1)

    print(f"✅ Found test user: {test_user.email} (ID: {test_user.id})")

    # Get or create loyalty account
    loyalty_account = db.query(models.LoyaltyAccount).filter(
        models.LoyaltyAccount.user_id == test_user.id
    ).first()

    if not loyalty_account:
        print("❌ Loyalty account not found for test user")
        print("Creating loyalty account...")
        loyalty_account = models.LoyaltyAccount(
            user_id=test_user.id,
            points_balance=500,
            tier_id=1  # Default tier
        )
        db.add(loyalty_account)
        db.commit()
        print(f"✅ Created loyalty account with 500 points")
    else:
        print(f"✅ Found loyalty account: {loyalty_account.points_balance} points")

    # Check existing redemptions
    existing = db.query(models.Redemption).filter(
        models.Redemption.loyalty_account_id == loyalty_account.id
    ).all()
    print(f"\n📊 Existing redemptions: {len(existing)}")
    for r in existing:
        print(f"   - Code: {r.reward_code}, Value: ${r.reward_value}, Status: {r.status}")

    # Create test discount codes
    test_codes = [
        {"code": "WELCOME20", "value": 20, "description": "Welcome discount"},
        {"code": "SAVE10", "value": 10, "description": "Save 10 dollars"},
        {"code": "LUCKY50", "value": 50, "description": "Lucky 50 dollar discount"},
    ]

    print(f"\n📝 Creating {len(test_codes)} test discount codes...")

    for code_data in test_codes:
        # Check if code already exists
        existing_code = db.query(models.Redemption).filter(
            models.Redemption.reward_code == code_data["code"],
            models.Redemption.loyalty_account_id == loyalty_account.id
        ).first()

        if existing_code:
            print(f"   ⚠️  Code '{code_data['code']}' already exists (ID: {existing_code.id})")
            continue

        # Create redemption
        redemption = models.Redemption(
            loyalty_account_id=loyalty_account.id,
            reward_code=code_data["code"],
            reward_value=code_data["value"],
            redemption_type="discount_code",
            status="active",
            expires_at=datetime.utcnow() + timedelta(days=30),  # Expires in 30 days
            created_at=datetime.utcnow()
        )
        db.add(redemption)
        db.commit()
        print(f"   ✅ Created code '{code_data['code']}' - ${code_data['value']} (ID: {redemption.id})")

    print(f"\n" + "=" * 80)
    print("TEST DISCOUNT CODES CREATED SUCCESSFULLY")
    print("=" * 80)
    print("\n🧪 Test with these codes at checkout:")
    for code_data in test_codes:
        print(f"   • {code_data['code']} - ${code_data['value']} off")
    
    print(f"\n📍 Test user: customer1@marketplace.com / password123")
    print(f"📍 User ID: {test_user.id}")
    print(f"📍 Loyalty Account ID: {loyalty_account.id}")
    print("=" * 80)

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
