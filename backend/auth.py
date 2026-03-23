from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import hashlib
import os
import secrets
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import User, SessionLocal, get_db

# --- Configuration ---
APP_ENV = os.getenv("APP_ENV", "development").lower()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if APP_ENV in {"development", "dev", "test"}:
        import warnings
        SECRET_KEY = "dev-only-fallback-key-CHANGE-IN-PRODUCTION"
        warnings.warn("SECRET_KEY not set. Using insecure fallback for development only.", stacklevel=2)
    else:
        raise RuntimeError("SECRET_KEY environment variable must be set outside development/test.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day
SESSION_COOKIE_NAME = "admin_session"
CSRF_COOKIE_NAME = "csrf_token"

# --- Password Hashing with raw bcrypt ---
# Uses SHA-256 pre-hashing to safely handle any password length/encoding.
# This is the same approach used by Dropbox and recommended by security experts.
# bcrypt has a 72-byte limit, so we normalize passwords to a 64-char hex digest first.

# --- OAuth2 Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

# --- Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    username: Optional[str] = None

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Helper Functions ---

def _prehash_password(password) -> bytes:
    """SHA-256 pre-hash to normalize password to 64-byte hex string.
    This ensures bcrypt never receives >72 bytes, regardless of
    password length or unicode character encoding."""
    if isinstance(password, str):
        password = password.encode('utf-8')
    return hashlib.sha256(password).hexdigest().encode('utf-8')

def verify_password(plain_password, hashed_password):
    """Verify a plain password against a bcrypt hash."""
    prehashed = _prehash_password(plain_password)
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(prehashed, hashed_password)

def get_password_hash(password):
    """Hash a password using SHA-256 pre-hash + bcrypt."""
    prehashed = _prehash_password(password)
    return bcrypt.hashpw(prehashed, bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)

async def get_session_payload(request: Request):
    bearer_token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()

    token = bearer_token or request.cookies.get(SESSION_COOKIE_NAME)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

async def get_current_user(payload: dict = Depends(get_session_payload), db: Session = Depends(get_db)):
    token_data = TokenData(username=payload.get("sub"))
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def verify_csrf(request: Request, payload: dict = Depends(get_session_payload)):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return

    header_token = request.headers.get("X-CSRF-Token")
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    payload_token = payload.get("csrf")

    if not header_token or not cookie_token or not payload_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")

    if not secrets.compare_digest(header_token, cookie_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch")

    if not secrets.compare_digest(header_token, payload_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid")
