from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
from app.config import settings
from app.models import User, UserCreate, UserRole
from app.database import get_collection
from app.core.redis_client import TokenBlacklist

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

async def create_user(user_data: UserCreate) -> User:
    users_col = get_collection("users")
    
    # Check if user exists
    existing = await users_col.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    now = datetime.utcnow()
    user_doc = {
        "email": user_data.email,
        "phone": user_data.phone,
        "full_name": user_data.full_name,
        "hashed_password": get_password_hash(user_data.password),
        "role": user_data.role,
        "is_active": True,
        "created_at": now,
        "updated_at": now
    }
    
    result = await users_col.insert_one(user_doc)
    user_doc["id"] = str(result.inserted_id)
    
    return User(**user_doc)

async def authenticate_user(email: str, password: str) -> Optional[User]:
    users_col = get_collection("users")
    user_doc = await users_col.find_one({"email": email})
    
    if not user_doc:
        return None
    if not verify_password(password, user_doc["hashed_password"]):
        return None
    
    user_doc["id"] = str(user_doc["_id"])
    return User(**user_doc)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )
    
    # Check if token is blacklisted
    if await TokenBlacklist.is_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if not user_id or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    users_col = get_collection("users")
    user_doc = await users_col.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise credentials_exception
    
    user_doc["id"] = str(user_doc["_id"])
    return User(**user_doc)

async def logout_user(token: str) -> bool:
    """Logout user by blacklisting their token"""
    try:
        # Get token expiration to set appropriate blacklist TTL
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp = payload.get("exp", 0)
        
        # Calculate remaining time in seconds
        now = datetime.utcnow().timestamp()
        ttl = max(int(exp - now), 0)
        
        if ttl > 0:
            await TokenBlacklist.add(token, ttl)
        
        return True
    except Exception:
        return False
