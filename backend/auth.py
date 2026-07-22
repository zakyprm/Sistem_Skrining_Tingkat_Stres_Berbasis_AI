"""
auth.py — Modul autentikasi JWT untuk Ustadz/Konselor

Menyediakan:
- Hashing & verifikasi password (bcrypt via passlib)
- Pembuatan & validasi JWT (python-jose)
- FastAPI dependency get_current_user — dipakai di endpoint yang dilindungi
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

# ─── Konfigurasi ─────────────────────────────────────────────────────
ALGORITHM = "HS256"

def _get_secret_key() -> str:
    key = os.environ.get("SECRET_KEY", "")
    if not key:
        raise RuntimeError(
            "[AUTH] SECRET_KEY tidak ditemukan di environment. "
            "Tambahkan SECRET_KEY ke file .env."
        )
    return key

def _get_expire_minutes() -> int:
    try:
        return int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    except ValueError:
        return 480

# ─── Password hashing (bcrypt langsung, kompatibel bcrypt 5.x) ──────
def hash_password(plain_password: str) -> str:
    """Hash password plaintext menggunakan bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifikasi password plaintext terhadap hash bcrypt."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8'),
        )
    except Exception:
        return False


# ─── JWT Token ───────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Buat JWT access token.

    Args:
        data: Payload yang akan di-encode (minimal {"sub": username, "role": role})
        expires_delta: Durasi berlaku token (default dari env ACCESS_TOKEN_EXPIRE_MINUTES)

    Returns:
        str: JWT token sebagai string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=_get_expire_minutes())
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode dan validasi JWT token.

    Returns:
        dict: Payload token jika valid

    Raises:
        JWTError: Jika token tidak valid atau kadaluarsa
    """
    return jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])


# ─── FastAPI Security Scheme ─────────────────────────────────────────
# Menggunakan HTTPBearer agar Swagger UI bisa langsung test dengan token
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """
    FastAPI dependency: validasi JWT dari header Authorization: Bearer <token>.

    Returns:
        dict: Payload token {"sub": username, "role": role}

    Raises:
        HTTPException 401: Jika token tidak ada, tidak valid, atau kadaluarsa
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        payload = decode_access_token(credentials.credentials)
        username: str = payload.get("sub", "")
        if not username:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception
