from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from typing import Optional

from app.database.connection import get_users_collection
from app.database.models import user_helper
from app.auth.jwt_handler import decode_token

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    token: Optional[str] = Query(None),
) -> dict:
    """
    Get current user from JWT token or API key.
    Supports both Authorization: Bearer <token> and X-API-Key header.
    """
    users_collection = get_users_collection()
    user = None
    
    # Try JWT token (Header or Query)
    token_to_decode = None
    if credentials:
        token_to_decode = credentials.credentials
    elif token:
        token_to_decode = token

    if token_to_decode:
        payload = decode_token(token_to_decode)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                user = await users_collection.find_one({"_id": user_id})
    
    # Try API key if no JWT
    if not user and api_key:
        user = await users_collection.find_one({"api_key": api_key})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a valid Bearer token or API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled."
        )
    
    return user_helper(user)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    token: Optional[str] = Query(None),
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.
    Used for endpoints that work both with and without auth.
    """
    try:
        return await get_current_user(credentials, api_key, token)
    except HTTPException:
        return None


async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Require admin privileges."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required."
        )
    return current_user
