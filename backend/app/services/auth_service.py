"""
Firestore-only authentication service.
Handles password hashing, reset tokens, and credential validation without Firebase Auth SDK.
"""

import bcrypt
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional
from google.cloud.firestore import Client
from pydantic import BaseModel


class ResetToken(BaseModel):
    """Password reset token stored in Firestore."""
    token: str
    created_at: datetime
    expires_at: datetime
    used: bool = False


class FirestoreAuthService:
    """
    Firestore-based auth service for student login.
    Stores hashed passwords and manages password resets.
    """

    def __init__(self, db: Client):
        self.db = db
        self.users_collection = db.collection("users")
        self.tokens_collection = db.collection("password_reset_tokens")
        self.token_expiry_hours = 24

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    def generate_reset_token(self) -> str:
        """Generate a secure reset token."""
        return secrets.token_urlsafe(32)

    def create_student_credentials(self, uid: str, email: str, password: str) -> bool:
        """
        Create student credentials in Firestore.
        
        Args:
            uid: User ID (from signup)
            email: Student email
            password: Plain text password to hash
            
        Returns:
            True if successful, False otherwise
        """
        try:
            hashed_pwd = self.hash_password(password)
            now = datetime.utcnow()

            # Update user document with password hash
            self.users_collection.document(uid).update({
                "password_hash": hashed_pwd,
                "email": email,
                "auth_method": "firestore",
                "last_password_change": now.isoformat(),
                "created_credentials_at": now.isoformat(),
            })
            return True
        except Exception as e:
            print(f"Error creating credentials: {e}")
            return False

    def verify_student_login(self, email: str, password: str) -> Optional[str]:
        """
        Verify student email/password.
        
        Args:
            email: Student email
            password: Plain text password
            
        Returns:
            uid if successful, None if failed
        """
        try:
            # Query user by email
            users = self.users_collection.where("email", "==", email).stream()
            user_doc = next(users, None)

            if not user_doc:
                return None

            user_data = user_doc.to_dict()
            password_hash = user_data.get("password_hash")

            if not password_hash:
                return None

            # Verify password
            if self.verify_password(password, password_hash):
                return user_doc.id
            
            return None
        except Exception as e:
            print(f"Error verifying login: {e}")
            return None

    def get_student_profile(self, uid: str) -> dict:
        """Return the stored user profile for login/session restoration."""
        try:
            user_doc = self.users_collection.document(uid).get()
            if not user_doc.exists:
                return {}
            profile = user_doc.to_dict()
            return profile if isinstance(profile, dict) else {}
        except Exception as e:
            print(f"Error loading profile: {e}")
            return {}

    def create_password_reset_token(self, email: str) -> Optional[str]:
        """
        Create a password reset token for email.
        
        Args:
            email: Student email
            
        Returns:
            Reset token if user found, None otherwise
        """
        try:
            # Find user by email
            users = self.users_collection.where("email", "==", email).stream()
            user_doc = next(users, None)

            if not user_doc:
                return None

            uid = user_doc.id

            # Generate reset token
            token = self.generate_reset_token()
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=self.token_expiry_hours)

            # Store token in Firestore
            self.tokens_collection.document(token).set({
                "uid": uid,
                "email": email,
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "used": False,
            })

            return token
        except Exception as e:
            print(f"Error creating reset token: {e}")
            return None

    def verify_reset_token(self, token: str) -> Optional[str]:
        """
        Verify and return UID if token is valid.
        
        Args:
            token: Reset token
            
        Returns:
            uid if valid, None otherwise
        """
        try:
            token_doc = self.tokens_collection.document(token).get()

            if not token_doc.exists:
                return None

            token_data = token_doc.to_dict()
            expires_at = datetime.fromisoformat(token_data.get("expires_at", ""))
            used = token_data.get("used", False)

            # Check expiry and if already used
            if datetime.utcnow() > expires_at or used:
                return None

            return token_data.get("uid")
        except Exception as e:
            print(f"Error verifying reset token: {e}")
            return None

    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using token.
        
        Args:
            token: Reset token
            new_password: New plain text password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify token
            uid = self.verify_reset_token(token)
            if not uid:
                return False

            # Get token document
            token_doc = self.tokens_collection.document(token).get()
            token_data = token_doc.to_dict()

            # Hash new password
            hashed_pwd = self.hash_password(new_password)
            now = datetime.utcnow()

            # Update user password
            self.users_collection.document(uid).update({
                "password_hash": hashed_pwd,
                "last_password_change": now.isoformat(),
            })

            # Mark token as used
            self.tokens_collection.document(token).update({
                "used": True,
                "used_at": now.isoformat(),
            })

            return True
        except Exception as e:
            print(f"Error resetting password: {e}")
            return False

    def cleanup_expired_tokens(self) -> int:
        """Delete expired reset tokens (run periodically as cleanup task)."""
        try:
            now = datetime.utcnow()
            expired = self.tokens_collection.where(
                "expires_at", "<", now.isoformat()
            ).stream()

            count = 0
            for doc in expired:
                doc.reference.delete()
                count += 1

            return count
        except Exception as e:
            print(f"Error cleaning tokens: {e}")
            return 0
