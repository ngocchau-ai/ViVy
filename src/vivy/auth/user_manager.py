"""
User Manager & Authentication Layer — Argon2id Password Hashing, JWT & Global Session Revocation.
"""

from dataclasses import dataclass
import datetime
import hashlib
import hmac
import json
import logging
import os
import sqlite3
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("VIVY_JWT_SECRET", "ngoc-chau-vivy-secure-secret-key-2026")


@dataclass
class User:
    username: str
    role: str  # admin, trader, analyst
    created_at: str


class UserAuthenticationManager:
    """Manages user registration, Argon2id/SHA256 authentication, JWT tokens, and global session invalidation."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or ":memory:"
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._min_valid_timestamp: float = 0.0
        self._init_db()

    def _init_db(self):
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT,
                    role TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Secure password hashing using SHA256 + Salt (or Argon2id if installed)."""
        try:
            from passlib.hash import argon2
            return argon2.hash(password)
        except ImportError:
            salt = "ngoc_chau_salt_2026"
            return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        try:
            from passlib.hash import argon2
            return argon2.verify(password, password_hash)
        except ImportError:
            salt = "ngoc_chau_salt_2026"
            computed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
            return hmac.compare_digest(computed, password_hash)

    def register_user(self, username: str, password: str, role: str = "trader") -> User:
        p_hash = self._hash_password(password)
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, p_hash, role, now_str)
            )
        return User(username=username, role=role, created_at=now_str)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT username, password_hash, role, created_at FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and self._verify_password(password, row[1]):
            return User(username=row[0], role=row[2], created_at=row[3])
        return None

    def revoke_all_sessions(self):
        """Invalidates all sessions created prior to current time."""
        self._min_valid_timestamp = datetime.datetime.now(datetime.timezone.utc).timestamp()
        logger.info(f"Global session invalidation executed at {self._min_valid_timestamp}")

    def create_jwt_token(self, user: User, expires_minutes: int = 60) -> str:
        """Generates JWT bearer token with issued-at timestamp."""
        now = datetime.datetime.now(datetime.timezone.utc)
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user.username,
            "role": user.role,
            "iat": now.timestamp(),
            "exp": (now + datetime.timedelta(minutes=expires_minutes)).timestamp()
        }
        
        def b64url(data: bytes) -> str:
            import base64
            return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

        h_b64 = b64url(json.dumps(header).encode("utf-8"))
        p_b64 = b64url(json.dumps(payload).encode("utf-8"))
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        
        signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = b64url(signature)

        return f"{h_b64}.{p_b64}.{sig_b64}"

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validates JWT signature, expiration, and checks session revocation."""
        try:
            import base64
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            h_b64, p_b64, sig_b64 = parts
            signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
            expected_sig = base64.urlsafe_b64encode(
                hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
            ).decode("utf-8").rstrip("=")

            if not hmac.compare_digest(sig_b64, expected_sig):
                return None

            # Decode payload
            padding = "=" * (4 - len(p_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(p_b64 + padding).decode("utf-8"))

            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            if payload.get("exp", 0) < now:
                return None

            if payload.get("iat", 0) < self._min_valid_timestamp:
                logger.warning("Token rejected due to session revocation.")
                return None

            return payload
        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            return None
