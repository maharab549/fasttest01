#!/usr/bin/env python3
"""
Test Payment Method and Withdrawal System
Tests the complete seller payment workflow
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

# Test user credentials
TEST_SELLER_EMAIL = "seller@test.com"
TEST_SELLER_PASSWORD = "testpass123"
TEST_SELLER_USERNAME = "testseller"
TEST_SELLER_NAME = "Test Seller"

def log_test(title: str, status: str = "", details: str = ""):
    """Pretty print test results"""
    print(f"\n{'='*60}")
    print(f"TEST: {title}")
    if status:
        print(f"STATUS: {status}")
    if details:
        print(f"DETAILS: {details}")

def log_response(response):
    """Print response details"""
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

class PaymentSystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.seller_id = None

    def register_seller(self) -> bool:
        """Register a new seller account"""
        log_test("Register Seller Account")
        
        payload = {
            "email": TEST_SELLER_EMAIL,
            "username": TEST_SELLER_USERNAME,
            "full_name": TEST_SELLER_NAME,
            "password": TEST_SELLER_PASSWORD,
            "is_seller": True
        }
        
        response = self.session.post(
            f"{BASE_URL}/auth/register",
            json=payload
        )
        
        log_response(response)
        
        if response.status_code in [200, 201]:
            log_test("Register Seller", "✓ PASSED")
            return True
        else:
            log_test("Register Seller", "✗ FAILED")
            return False

    def login_seller(self) -> bool:
        """Login as seller"""
        log_test("Login Seller Account")
        
        payload = {
            "username": TEST_SELLER_USERNAME,
            "password": TEST_SELLER_PASSWORD
        }
        
        response = self.session.post(
            f"{BASE_URL}/auth/token",
            data=payload
        )
        
        log_response(response)
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            log_test("Login Seller", "✓ PASSED")
            return True
        else:
            log_test("Login Seller", "✗ FAILED")
            return False

    def get_seller_profile(self) -> bool:
        """Get seller profile"""
        log_test("Get Seller Profile")
        
        response = self.session.get(f"{BASE_URL}/seller/profile")
        
        log_response(response)
        
        if response.status_code == 200:
            data = response.json()
            self.seller_id = data.get("id")
            log_test("Get Seller Profile", "✓ PASSED")
            return True
        else:
            log_test("Get Seller Profile", "✗ FAILED")
            return False

    def get_payout_info(self) -> bool:
        """Get existing payout info"""
        log_test("GET /seller/payout-info - Get Existing Payment Method")
        
        response = self.session.get(f"{BASE_URL}/seller/payout-info")
        
        log_response(response)
        
        if response.status_code == 200:
            log_test("Get Payout Info", "✓ PASSED")
            return True
        else:
            log_test("Get Payout Info", "✗ FAILED")
            return False

    def update_payout_info_bank(self) -> bool:
        """Update payout info with bank transfer details"""
        log_test("PUT /seller/payout-info - Save Bank Transfer Payment Method")
        
        payload = {
            "method_type": "bank_transfer",
            "bank_account": "DE89370400440532013000",
            "bank_code": "DEUTDEFF500",
            "account_holder_name": "Test Seller",
            "email": "seller@test.com"
        }
        
        response = self.session.put(
            f"{BASE_URL}/seller/payout-info",
            json=payload
        )
        
        log_response(response)
        
        if response.status_code == 200:
            log_test("Update Payout Info (Bank)", "✓ PASSED")
            return True
        else:
            log_test("Update Payout Info (Bank)", "✗ FAILED")
            return False

    def update_payout_info_paypal(self) -> bool:
        """Update payout info with PayPal"""
        log_test("PUT /seller/payout-info - Save PayPal Payment Method")
        
        payload = {
            "method_type": "paypal",
            "email": "seller@paypal.com"
        }
        
        response = self.session.put(
            f"{BASE_URL}/seller/payout-info",
            json=payload
        )
        
        log_response(response)
        
        if response.status_code == 200:
            log_test("Update Payout Info (PayPal)", "✓ PASSED")
            return True
        else:
            log_test("Update Payout Info (PayPal)", "✗ FAILED")
            return False

    def update_payout_info_stripe(self) -> bool:
        """Update payout info with Stripe"""
        log_test("PUT /seller/payout-info - Save Stripe Payment Method")
        
        payload = {
            "method_type": "stripe",
            "email": "seller@stripe.com"
        }
        
        response = self.session.put(
            f"{BASE_URL}/seller/payout-info",
            json=payload
        )
        
        log_response(response)
        
        if response.status_code == 200:
            log_test("Update Payout Info (Stripe)", "✓ PASSED")
            return True
        else:
            log_test("Update Payout Info (Stripe)", "✗ FAILED")
            return False

    def request_withdrawal(self, amount: float = 50.0) -> bool:
        """Request withdrawal"""
        log_test(f"POST /seller/withdraw - Request ${amount} Withdrawal")
        
        payload = {
            "amount": amount
        }
        
        response = self.session.post(
            f"{BASE_URL}/seller/withdraw",
            json=payload
        )
        
        log_response(response)
        
        if response.status_code == 200:
            log_test(f"Request Withdrawal (${amount})", "✓ PASSED")
            return True
        else:
            log_test(f"Request Withdrawal (${amount})", "✗ FAILED")
            return False

    def get_withdrawals(self) -> bool:
        """Get withdrawal history"""
        log_test("GET /seller/withdrawals - Get Withdrawal History")
        
        response = self.session.get(f"{BASE_URL}/seller/withdrawals")
        
        log_response(response)
        
        if response.status_code == 200:
            log_test("Get Withdrawals", "✓ PASSED")
            return True
        else:
            log_test("Get Withdrawals", "✗ FAILED")
            return False

    def run_all_tests(self):
        """Run complete payment system test suite"""
        print("\n" + "="*60)
        print("MEGAMART PAYMENT SYSTEM TEST SUITE")
        print("="*60)
        
        tests = [
            ("Register Seller", self.register_seller),
            ("Login Seller", self.login_seller),
            ("Get Seller Profile", self.get_seller_profile),
            ("Get Payout Info (initial)", self.get_payout_info),
            ("Update Payout Info (Bank)", self.update_payout_info_bank),
            ("Get Payout Info (after update)", self.get_payout_info),
            ("Update Payout Info (PayPal)", self.update_payout_info_paypal),
            ("Update Payout Info (Stripe)", self.update_payout_info_stripe),
            ("Request Withdrawal", self.request_withdrawal),
            ("Get Withdrawals", self.get_withdrawals),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"\n✗ EXCEPTION in {test_name}: {str(e)}")
                failed += 1
        
        print("\n" + "="*60)
        print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED")
        print("="*60 + "\n")

if __name__ == "__main__":
    print("Ensure the backend server is running on http://localhost:8000")
    print("Press Enter to start tests...")
    input()
    
    tester = PaymentSystemTester()
    tester.run_all_tests()
