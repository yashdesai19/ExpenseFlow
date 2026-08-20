from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict
import bcrypt
import jwt
from app.core.config import settings


# ------------------------------------------------------------------------------
# Password Hashing & Verification (Bcrypt)
# ------------------------------------------------------------------------------
def get_password_hash(password: str) -> str:
    """
    Hashes a plaintext password using bcrypt with automatic salting.
    Bcrypt incorporates a random 128-bit salt and an adaptive work factor (rounds).
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a stored bcrypt hash in constant time
    to prevent timing attacks.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


# ------------------------------------------------------------------------------
# JSON Web Token (JWT) Generation & Verification
# ------------------------------------------------------------------------------
def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Creates a cryptographically signed JWT access token.
    - 'sub' (subject): Stores the unique user identifier (e.g. user_id or email).
    - 'exp' (expiration): UTC timestamp after which the token is invalid.
    - 'iat' (issued at): UTC timestamp of when token was generated.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and validates the signature, structure, and expiration of a JWT token.
    Returns the decoded claims dictionary if valid, or None if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.PyJWTError:
        return None
