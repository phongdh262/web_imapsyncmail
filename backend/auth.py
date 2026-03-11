from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import hashlib
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import User, SessionLocal, get_db

# --- Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-fallback-key-CHANGE-IN-PRODUCTION")
if SECRET_KEY == "dev-only-fallback-key-CHANGE-IN-PRODUCTION":
    import warnings
    warnings.warn("⚠️ SECRET_KEY not set! Using insecure fallback. Set SECRET_KEY in .env for production.", stacklevel=2)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

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


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user
