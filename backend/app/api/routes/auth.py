from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

import os
import secrets
import firebase_admin
from firebase_admin import credentials as fb_credentials, auth as fb_auth

from ...core.firestore_client import FIRESTORE_TIMEOUT_SECONDS, get_firestore_client
from ...schemas.user import StudentSignupRequest

# Path to service account key used elsewhere in the project
FIREBASE_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "firebase_key.json")

router = APIRouter(prefix="/api/auth", tags=["Onboarding"])

def get_db():
    return get_firestore_client()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def register_new_student(payload: StudentSignupRequest):
    """Saves dynamic user profile details into Firestore after phone OTP confirmation.

    Writes the user document first, then attempts to ensure a Firebase Auth user exists
    and generates a password-reset link. Auth operations are best-effort and will not
    fail the signup if Auth is not configured.
    """
    db = get_db()
    user_ref = db.collection("users").document(payload.uid)

    # Validation: Prevent duplicate accounts
    try:
        existing_user = user_ref.get(timeout=FIRESTORE_TIMEOUT_SECONDS)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Firestore unavailable during signup lookup: {str(e)}"
        )

    if existing_user.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student profile is already configured for this verified account."
        )

    current_time_iso = datetime.now(timezone.utc).isoformat()

    # Construct transactional cloud database payload
    database_record = {
        "uid": payload.uid,
        "role": "student",
        "created_at": current_time_iso,
        "last_login": current_time_iso,
        "personal_details": payload.personal_details.dict(),
        "parent_details": payload.parent_details.dict(),
        "academic_profile": payload.academic_profile.dict(),
        "subscription": {
            "is_active": False,
            "subscribed_grade": None,
            "current_period_start": None,
            "current_period_end": None,
            "last_payment_id": None
        }
    }

    try:
        user_ref.set(database_record, timeout=FIRESTORE_TIMEOUT_SECONDS)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit database transaction: {str(e)}"
        )

    # Attempt to ensure a Firebase Auth user exists for this profile and create a password-reset link
    reset_link = None
    try:
        # Initialize firebase admin SDK if not already initialized
        if not firebase_admin._apps:
            cred = fb_credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred)

        email = payload.personal_details.email
        uid = payload.uid

        try:
            existing = fb_auth.get_user(uid)
            # If the auth user exists but has no email, set the email
            if email and not existing.email:
                fb_auth.update_user(uid, email=email)
        except fb_auth.UserNotFoundError:
            # Create an auth user with a temporary password and ask user to reset
            temp_pw = secrets.token_urlsafe(12)
            fb_auth.create_user(uid=uid, email=email, password=temp_pw, display_name=payload.personal_details.full_name)

        # Generate a password reset link so the user can set their own password
        if email:
            reset_link = fb_auth.generate_password_reset_link(email)
    except Exception:
        # Do not fail signup if Auth operations are not available or misconfigured
        reset_link = None

    response = {"status": "success", "message": f"Successfully onboarded {payload.personal_details.full_name}."}
    if reset_link:
        response["password_reset_link"] = reset_link

    return response
