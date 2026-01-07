from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

from app.database.connection import get_users_collection
from app.database.models import generate_id, user_helper
from app.auth.jwt_handler import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    decode_token,
    generate_api_key,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.auth.schemas import (
    UserCreate, 
    UserLogin, 
    UserResponse, 
    TokenResponse, 
    TokenRefresh,
    APIKeyResponse
)
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user."""
    users = get_users_collection()
    
    # Check if email exists
    if await users.find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    
    # Check if username exists
    if await users.find_one({"username": user_data.username}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken."
        )
    
    # Create user document
    user_doc = {
        "_id": generate_id(),
        "email": user_data.email,
        "username": user_data.username,
        "hashed_password": get_password_hash(user_data.password),
        "is_active": True,
        "is_admin": False,
        "api_key": None,
        "rate_limit_per_minute": 60,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    await users.insert_one(user_doc)
    
    return user_helper(user_doc)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and get access/refresh tokens."""
    users = get_users_collection()
    user = await users.find_one({"email": credentials.email})
    
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled."
        )
    
    # Create tokens
    token_data = {"sub": user["_id"], "email": user["email"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefresh):
    """Refresh access token using refresh token."""
    payload = decode_token(token_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token."
        )
    
    user_id = payload.get("sub")
    users = get_users_collection()
    user = await users.find_one({"_id": user_id})
    
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive."
        )
    
    # Create new tokens
    new_token_data = {"sub": user["_id"], "email": user["email"]}
    access_token = create_access_token(new_token_data)
    new_refresh_token = create_refresh_token(new_token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.post("/api-key", response_model=APIKeyResponse)
async def generate_new_api_key(current_user: dict = Depends(get_current_user)):
    """Generate a new API key for the current user."""
    users = get_users_collection()
    new_api_key = generate_api_key()
    
    await users.update_one(
        {"_id": current_user["id"]},
        {"$set": {"api_key": new_api_key, "updated_at": datetime.utcnow()}}
    )
    
    return APIKeyResponse(api_key=new_api_key)


@router.delete("/api-key", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(current_user: dict = Depends(get_current_user)):
    """Revoke current API key."""
    users = get_users_collection()
    
    await users.update_one(
        {"_id": current_user["id"]},
        {"$set": {"api_key": None, "updated_at": datetime.utcnow()}}
    )
