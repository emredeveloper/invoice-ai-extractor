import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from typing import Callable

# Get rate limit from env or use default
DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "60/minute")
UPLOAD_RATE_LIMIT = os.getenv("UPLOAD_RATE_LIMIT", "10/minute")


def get_user_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting.
    Uses user ID if authenticated, otherwise uses IP.
    """
    # Check for user in request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.id}"
    
    # Check for API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key[:16]}"
    
    # Fall back to IP
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/1")
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail),
            "retry_after": exc.retry_after
        },
        headers={"Retry-After": str(exc.retry_after)}
    )


# Decorator shortcuts for common limits
def limit_uploads(func: Callable) -> Callable:
    """Rate limit decorator for upload endpoints."""
    return limiter.limit(UPLOAD_RATE_LIMIT)(func)


def limit_default(func: Callable) -> Callable:
    """Rate limit decorator with default limit."""
    return limiter.limit(DEFAULT_RATE_LIMIT)(func)
