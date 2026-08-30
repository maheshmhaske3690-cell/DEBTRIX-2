"""
Security helpers:
- password hashing (for basic email/password login)
- JWT session tokens
- Fernet encryption for GitHub access tokens stored at rest
  (required — see schema.sql notes: tokens must never be stored
  in plaintext, even in a private DB)
"""
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except Exception:
        return None


def encrypt_token(raw_token: str) -> str:
    """Encrypt a GitHub access token before storing it in the DB."""
    return _fernet.encrypt(raw_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a GitHub access token read from the DB, for use in API calls."""
    return _fernet.decrypt(encrypted_token.encode()).decode()
