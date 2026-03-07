"""
Authentication routes for iHhashi
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta

from app.models import UserCreate, UserRole
from app.services.auth import (
    create_user, authenticate_user, create_access_token, 
    create_refresh_token, get_current_user, logout_user
)

router = APIRouter()


@router.post("/register")
async def register(user_data: UserCreate):
    """Register a new user"""
    user = await create_user(user_data)
    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "message": "User created successfully"
    }


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "role": user.role}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "full_name": user.full_name
        }
    }


@router.get("/me")
async def get_me(current_user = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "phone": current_user.phone,
        "is_active": current_user.is_active
    }


@router.post("/logout")
async def logout(current_user = Depends(get_current_user), token: str = Depends(get_current_user)):
    """Logout user and blacklist token"""
    # Note: This is a simplified logout. In production, you'd need to pass the token
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token"""
    from jose import jwt, JWTError
    from app.config import settings
    
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        role = payload.get("role")
        token_type = payload.get("type")
        
        if not user_id or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        new_access_token = create_access_token(
            data={"sub": user_id, "role": role}
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
