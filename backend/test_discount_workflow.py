"""
Test discount code functionality end-to-end
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def test_discount_workflow():
    """Test the complete discount workflow"""
    
    # 1. Login
    print("1️⃣ Login...")
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "customer1@marketplace.com", "password": "password123"}
    )
    if login_resp.status_code != 200:
        print(f"❌ Login failed: {login_resp.status_code}")
        print(login_resp.text)
        return
    
    token = login_resp.json()['access_token']
    user_id = login_resp.json()['user']['id']
    print(f"✅ Logged in as user {user_id}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Check loyalty account
    print("\n2️⃣ Checking loyalty account...")
    loyalty_resp = requests.get(
        f"{BASE_URL}/loyalty/account",
        headers=headers
    )
    if loyalty_resp.status_code != 200:
        print(f"❌ No loyalty account: {loyalty_resp.status_code}")
        print(loyalty_resp.text)
        return
    
    loyalty_data = loyalty_resp.json()
    current_points = loyalty_data.get('points_balance', 0)
    print(f"✅ Current points: {current_points}")
    
    # 3. Check for existing redemptions
    print("\n3️⃣ Checking for active redemption codes...")
    redemptions_resp = requests.get(
        f"{BASE_URL}/loyalty/redemptions",
        headers=headers
    )
    if redemptions_resp.status_code != 200:
        print(f"❌ Failed to get redemptions: {redemptions_resp.status_code}")
        print(redemptions_resp.text)
        return
    
    redemptions = redemptions_resp.json()
    print(f"✅ Total redemptions: {len(redemptions)}")
    
    active_codes = [r for r in redemptions if r.get('status') == 'active']
    print(f"✅ Active codes: {len(active_codes)}")
    
    if len(active_codes) > 0:
        for code in active_codes:
            print(f"   - {code.get('reward_code')}: ${code.get('reward_value')} (expires: {code.get('expires_at')})")
            
            # 4. Test validating this code
            print(f"\n4️⃣ Testing discount validation for code: {code.get('reward_code')}")
            validate_resp = requests.post(
                f"{BASE_URL}/orders/validate-discount",
                headers=headers,
                params={"code": code.get('reward_code')}
            )
            
            if validate_resp.status_code == 200:
                result = validate_resp.json()
                print(f"✅ Code validated successfully!")
                print(f"   - Valid: {result.get('valid')}")
                print(f"   - Amount: ${result.get('discount_amount')}")
                print(f"   - Message: {result.get('message')}")
                print(f"   - Redemption ID: {result.get('redemption_id')}")
            else:
                print(f"❌ Validation failed: {validate_resp.status_code}")
                print(validate_resp.json())
    else:
        print("⚠️  No active codes found. Need to generate one first.")
        
        # Check if we have points to redeem
        if current_points >= 1000:  # Assuming 1000 points = $10
            print(f"\n📊 Redeeming {1000} points for discount code...")
            redeem_resp = requests.post(
                f"{BASE_URL}/loyalty/redeem",
                headers=headers,
                json={"points_to_redeem": 1000}
            )
            
            if redeem_resp.status_code == 201:
                redemption = redeem_resp.json()
                print(f"✅ Redeemed! Generated code: {redemption.get('reward_code')}")
                
                # Now test this new code
                code = redemption.get('reward_code')
                print(f"\n4️⃣ Testing new discount code: {code}")
                validate_resp = requests.post(
                    f"{BASE_URL}/orders/validate-discount",
                    headers=headers,
                    params={"code": code}
                )
                
                if validate_resp.status_code == 200:
                    result = validate_resp.json()
                    print(f"✅ New code validated successfully!")
                    print(f"   - Amount: ${result.get('discount_amount')}")
                else:
                    print(f"❌ Validation failed: {validate_resp.status_code}")
                    print(validate_resp.json())
            else:
                print(f"❌ Redemption failed: {redeem_resp.status_code}")
                print(redeem_resp.text)
        else:
            print(f"⚠️  Insufficient points ({current_points}) to redeem (need 1000+)")

if __name__ == "__main__":
    print("🧪 Testing Discount Code Workflow\n")
    print("=" * 60)
    test_discount_workflow()
    print("=" * 60)
