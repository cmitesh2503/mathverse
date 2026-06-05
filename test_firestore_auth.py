#!/usr/bin/env python
"""
Test Firestore-only authentication endpoints.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
ENDPOINT_BASE = f"{BASE_URL}/api/auth/firestore"

# Use a consistent test email for this session
TEST_UID = f"firestore_test_{int(datetime.now().timestamp())}"
TEST_EMAIL = f"firestore_test+{int(datetime.now().timestamp())}@example.com"
TEST_PASSWORD = "SecurePassword123!"
NEW_PASSWORD = "NewSecurePassword456!"

print("\n" + "=" * 80)
print("FIRESTORE-ONLY AUTH TEST SUITE")
print("=" * 80)

# Test 1: Create credentials for existing user
print("\n[TEST 1] Create credentials for existing user")
print("-" * 80)

# First, ensure user exists in Firestore by creating profile via signup
signup_payload = {
    "uid": TEST_UID,
    "personal_details": {
        "full_name": "Firestore Auth Test",
        "email": TEST_EMAIL,
        "mobile_no": "+919876543210",
        "address": {
            "street": "123 Test St",
            "city": "Delhi",
            "state": "Delhi",
            "pincode": "110001"
        }
    },
    "parent_details": {
        "parent_name": "Parent",
        "parent_mobile": "+919876543211"
    },
    "academic_profile": {
        "current_grade": "10",
        "school_board": "CBSE",
        "school_name": "Test School"
    }
}

print(f"Creating user profile via /api/auth/signup...")
try:
    resp = requests.post(f"{BASE_URL}/api/auth/signup", json=signup_payload, timeout=10)
    print(f"Status: {resp.status_code}")
    if resp.status_code != 201:
        print(f"Warning: Signup returned {resp.status_code}")
except Exception as e:
    print(f"Note: Signup result: {e}")

# Now create Firestore credentials
create_creds_payload = {
    "uid": TEST_UID,
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD
}

print(f"\nPayload: {json.dumps(create_creds_payload, indent=2)}\n")

try:
    resp = requests.post(
        f"{ENDPOINT_BASE}/create-credentials",
        json=create_creds_payload,
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    
    if resp.status_code == 201:
        print("✅ Credentials created successfully")
    else:
        print("❌ Failed to create credentials")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Login with email + password
print("\n[TEST 2] Login with email + password")
print("-" * 80)

login_payload = {
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD
}

print(f"Payload: {json.dumps(login_payload, indent=2)}\n")

login_response = None
try:
    resp = requests.post(
        f"{ENDPOINT_BASE}/login",
        json=login_payload,
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    
    if resp.status_code == 200:
        print("✅ Login successful")
        login_response = resp.json()
    else:
        print("❌ Login failed")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Verify login fails with wrong password
print("\n[TEST 3] Verify login fails with wrong password")
print("-" * 80)

wrong_password_payload = {
    "email": TEST_EMAIL,
    "password": "WrongPassword123!"
}

print(f"Attempting login with wrong password...\n")

try:
    resp = requests.post(
        f"{ENDPOINT_BASE}/login",
        json=wrong_password_payload,
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    
    if resp.status_code == 401:
        print("✅ Correctly rejected wrong password")
    else:
        print("❌ Should have rejected wrong password")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Request password reset token
print("\n[TEST 4] Request password reset token (forgot password)")
print("-" * 80)

forgot_password_payload = {
    "email": TEST_EMAIL
}

print(f"Payload: {json.dumps(forgot_password_payload, indent=2)}\n")

reset_token = None
try:
    resp = requests.post(
        f"{ENDPOINT_BASE}/forgot-password",
        json=forgot_password_payload,
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    response_data = resp.json()
    print(f"Response: {json.dumps(response_data, indent=2)}")
    
    if resp.status_code == 200:
        print("✅ Reset token created")
        reset_token = response_data.get("reset_token")
    else:
        print("❌ Failed to create reset token")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: Verify reset token
print("\n[TEST 5] Verify reset token is valid")
print("-" * 80)

if reset_token:
    print(f"Token: {reset_token[:20]}...\n")
    
    try:
        resp = requests.post(
            f"{ENDPOINT_BASE}/verify-token",
            params={"token": reset_token},
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        if resp.status_code == 200 and resp.json().get("valid"):
            print("✅ Token is valid")
        else:
            print("❌ Token validation failed")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("⚠️  No token to verify (failed in previous step)")

# Test 6: Reset password with token
print("\n[TEST 6] Reset password using token")
print("-" * 80)

if reset_token:
    reset_password_payload = {
        "token": reset_token,
        "new_password": NEW_PASSWORD
    }
    
    print(f"Payload: {json.dumps({'token': reset_token[:20] + '...', 'new_password': '***'}, indent=2)}\n")
    
    try:
        resp = requests.post(
            f"{ENDPOINT_BASE}/reset-password",
            json=reset_password_payload,
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        if resp.status_code == 200:
            print("✅ Password reset successfully")
        else:
            print("❌ Password reset failed")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("⚠️  No token available (failed in previous step)")

# Test 7: Login with new password
print("\n[TEST 7] Login with new password")
print("-" * 80)

if reset_token:
    new_login_payload = {
        "email": TEST_EMAIL,
        "password": NEW_PASSWORD
    }
    
    print(f"Attempting login with new password...\n")
    
    try:
        resp = requests.post(
            f"{ENDPOINT_BASE}/login",
            json=new_login_payload,
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        
        if resp.status_code == 200:
            print("✅ Login with new password successful")
        else:
            print("❌ Login with new password failed")
    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("⚠️  Skipped (password reset failed)")

# Test 8: Verify old password no longer works
print("\n[TEST 8] Verify old password no longer works")
print("-" * 80)

old_login_payload = {
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD
}

print(f"Attempting login with old password...\n")

try:
    resp = requests.post(
        f"{ENDPOINT_BASE}/login",
        json=old_login_payload,
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
    
    if resp.status_code == 401:
        print("✅ Old password correctly rejected")
    else:
        print("❌ Old password should not work")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("FIRESTORE AUTH TEST COMPLETE")
print("=" * 80 + "\n")
