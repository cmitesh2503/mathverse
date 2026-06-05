"""
Firestore-only authentication endpoints (fallback if Firebase Auth unavailable).
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.firestore_client import get_firestore_client
from app.services.auth_service import FirestoreAuthService

router = APIRouter(prefix="/api/auth/firestore", tags=["auth-firestore"])


def get_auth_service() -> FirestoreAuthService:
    return FirestoreAuthService(get_firestore_client())


class FirestoreLoginRequest(BaseModel):
    """Firestore-only login request."""
    email: EmailStr
    password: str


class FirestoreForgotPasswordRequest(BaseModel):
    """Firestore-only forgot password request."""
    email: EmailStr


class FirestoreResetPasswordRequest(BaseModel):
    """Reset password with token."""
    token: str
    new_password: str


class CreateCredentialsRequest(BaseModel):
    """Create Firestore credentials for existing user."""
    uid: str
    email: EmailStr
    password: str


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/create-credentials", status_code=201)
async def create_credentials(payload: CreateCredentialsRequest):
    """
    Create Firestore-only credentials for a student.
    Use this after signup if Firebase Auth is unavailable.
    
    **Endpoint**: `POST /api/auth/firestore/create-credentials`
    
    **Request**:
    ```json
    {
        "uid": "student123",
        "email": "student@example.com",
        "password": "secure_password_123"
    }
    ```
    
    **Response (201)**:
    ```json
    {
        "status": "success",
        "message": "Credentials created. Use email/password to login.",
        "uid": "student123",
        "auth_method": "firestore"
    }
    ```
    """
    try:
        auth_service = get_auth_service()
        success = auth_service.create_student_credentials(
            payload.uid,
            payload.email,
            payload.password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create credentials in Firestore."
            )

        return {
            "status": "success",
            "message": "Credentials created. Use email/password to login.",
            "uid": payload.uid,
            "auth_method": "firestore",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating credentials: {str(e)}"
        )


@router.post("/login", status_code=200)
async def login_student(payload: FirestoreLoginRequest):
    """
    Login student using Firestore credentials (email + password).
    
    **Endpoint**: `POST /api/auth/firestore/login`
    
    **Request**:
    ```json
    {
        "email": "student@example.com",
        "password": "secure_password_123"
    }
    ```
    
    **Response (200 - Success)**:
    ```json
    {
        "status": "success",
        "uid": "student123",
        "email": "student@example.com",
        "message": "Login successful",
        "session_expires_in_hours": 24
    }
    ```
    
    **Response (401 - Failure)**:
    ```json
    {
        "detail": "Invalid email or password"
    }
    ```
    """
    try:
        auth_service = get_auth_service()
        uid = auth_service.verify_student_login(payload.email, payload.password)

        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        profile = auth_service.get_student_profile(uid)
        personal_details = profile.get("personal_details") if isinstance(profile.get("personal_details"), dict) else {}
        academic_profile = profile.get("academic_profile") if isinstance(profile.get("academic_profile"), dict) else {}

        # TODO: Generate session token or JWT
        return {
            "status": "success",
            "uid": uid,
            "email": payload.email,
            "full_name": personal_details.get("full_name"),
            "grade": academic_profile.get("current_grade"),
            "message": "Login successful",
            "session_expires_in_hours": 24,
            "auth_method": "firestore",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.post("/forgot-password", status_code=200)
async def forgot_password(payload: FirestoreForgotPasswordRequest):
    """
    Request password reset token (Firestore-based).
    
    **Endpoint**: `POST /api/auth/firestore/forgot-password`
    
    **Request**:
    ```json
    {
        "email": "student@example.com"
    }
    ```
    
    **Response (200)**:
    ```json
    {
        "status": "success",
        "message": "Reset token sent to email",
        "reset_token": "abc123def456...",
        "expires_in_hours": 24
    }
    ```
    
    **Response (404)**:
    ```json
    {
        "detail": "No account found with this email"
    }
    ```
    """
    try:
        auth_service = get_auth_service()
        token = auth_service.create_password_reset_token(payload.email)

        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email"
            )

        # TODO: Send token via email service (SendGrid, etc.)
        # For now, return token in response (in production, only send via email)
        return {
            "status": "success",
            "message": "Reset token created",
            "reset_token": token,
            "expires_in_hours": 24,
            "note": "In production, token sent via email only",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.post("/reset-password", status_code=200)
async def reset_password(payload: FirestoreResetPasswordRequest):
    """
    Reset password using token (Firestore-based).
    
    **Endpoint**: `POST /api/auth/firestore/reset-password`
    
    **Request**:
    ```json
    {
        "token": "abc123def456...",
        "new_password": "new_secure_password_456"
    }
    ```
    
    **Response (200 - Success)**:
    ```json
    {
        "status": "success",
        "message": "Password reset successful"
    }
    ```
    
    **Response (400 - Invalid Token)**:
    ```json
    {
        "detail": "Invalid or expired reset token"
    }
    ```
    """
    try:
        if len(payload.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters"
            )

        auth_service = get_auth_service()
        success = auth_service.reset_password(payload.token, payload.new_password)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        return {
            "status": "success",
            "message": "Password reset successful. You can now login with new password.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.post("/verify-token", status_code=200)
async def verify_reset_token(token: str):
    """
    Verify if a reset token is valid (check expiry, not used, etc).
    
    **Endpoint**: `POST /api/auth/firestore/verify-token?token=abc123...`
    
    **Response (200 - Valid)**:
    ```json
    {
        "valid": true,
        "uid": "student123"
    }
    ```
    
    **Response (200 - Invalid)**:
    ```json
    {
        "valid": false
    }
    ```
    """
    auth_service = get_auth_service()
    uid = auth_service.verify_reset_token(token)
    return {"valid": uid is not None, "uid": uid}
