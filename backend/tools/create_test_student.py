import os
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, auth, firestore

# Config — change if you want different test credentials
TEST_EMAIL = "student.test@example.com"
TEST_PASSWORD = "TestPass123!"
FULL_NAME = "Test Student"

FIREBASE_KEY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "core", "firebase_key.json")


def main():
    cred = credentials.Certificate(FIREBASE_KEY)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    # 1) Create or ensure auth user
    try:
        user = auth.get_user_by_email(TEST_EMAIL)
        print(f"Auth user already exists: uid={user.uid}")
    except auth.UserNotFoundError:
        user = auth.create_user(email=TEST_EMAIL, password=TEST_PASSWORD, display_name=FULL_NAME)
        print(f"Created auth user: uid={user.uid}")

    uid = user.uid

    # 2) Create Firestore profile if missing
    db = firestore.client()
    user_ref = db.collection("users").document(uid)
    now_iso = datetime.now(timezone.utc).isoformat()

    if user_ref.get().exists:
        print("Firestore user profile already exists — updating basic fields.")
        user_ref.update({
            "personal_details.full_name": FULL_NAME,
            "last_login": now_iso
        })
    else:
        profile = {
            "uid": uid,
            "role": "student",
            "created_at": now_iso,
            "last_login": now_iso,
            "personal_details": {
                "full_name": FULL_NAME,
                "email": TEST_EMAIL,
            },
            "parent_details": {},
            "academic_profile": {},
            "subscription": {
                "is_active": False,
                "subscribed_grade": None,
                "current_period_start": None,
                "current_period_end": None,
                "last_payment_id": None
            }
        }
        user_ref.set(profile)
        print("Created Firestore user profile.")

    # 3) Generate password reset link so the user can self-reset
    link = auth.generate_password_reset_link(TEST_EMAIL)
    print("Password reset link (valid for the user to reset their password):")
    print(link)
    print()
    print("Summary:")
    print(f"  Email: {TEST_EMAIL}")
    print(f"  Initial password (you may change now): {TEST_PASSWORD}")
    print(f"  UID: {uid}")


if __name__ == '__main__':
    main()
