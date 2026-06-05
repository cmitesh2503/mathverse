import requests
import json
from datetime import datetime

# Test signup endpoint against running backend
BASE_URL = "http://127.0.0.1:8000"

test_signup_payload = {
    "uid": f"test_student_{int(datetime.now().timestamp())}",
    "personal_details": {
        "full_name": "Test Student",
        "email": f"test.student+{int(datetime.now().timestamp())}@example.com",
        "mobile_no": "+919876543210",
        "address": {
            "street": "123 Test Street",
            "city": "Delhi",
            "state": "Delhi",
            "pincode": "110001"
        }
    },
    "parent_details": {
        "parent_name": "Parent Name",
        "parent_mobile": "+919876543211"
    },
    "academic_profile": {
        "current_grade": "10",
        "school_board": "CBSE",
        "school_name": "Test School"
    }
}

print("=" * 70)
print("TESTING SIGNUP ENDPOINT")
print("=" * 70)
print(f"\nPayload:\n{json.dumps(test_signup_payload, indent=2)}\n")

try:
    response = requests.post(f"{BASE_URL}/api/auth/signup", json=test_signup_payload, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"\nResponse:\n{json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("\n✅ Signup successful!")
        if "password_reset_link" in response.json():
            print("\n🔐 Password Reset Link generated (Firebase Auth available):")
            print(response.json()["password_reset_link"][:80] + "...")
        else:
            print("\n⚠️  No password reset link (Firebase Auth not configured)")
    else:
        print("\n❌ Signup failed")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
