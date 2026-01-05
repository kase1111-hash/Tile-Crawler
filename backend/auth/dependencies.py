"""
Authentication dependencies for FastAPI routes.

Provides dependency injection for authenticated routes.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import User, TokenData
from .service import get_auth_service

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get the current authenticated user.

    Raises HTTPException 401 if not authenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = get_auth_service()
    token_data = auth_service.verify_token(credentials.credentials)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_user(token_data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Dependency to optionally get the current authenticated user.

    Returns None if not authenticated (doesn't raise exception).
    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if credentials is None:
        return None

    auth_service = get_auth_service()
    token_data = auth_service.verify_token(credentials.credentials)

    if token_data is None:
        return None

    user = auth_service.get_user(token_data.user_id)

    if user is None or not user.is_active:
        return None

    return user


def require_user_owns_save(user: User, save_player_id: str) -> None:
    """
    Verify that a user owns a save.

    The save's player_id should match the user's ID.
    """
    if str(user.id) != save_player_id and save_player_id != f"user_{user.id}":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this save"
        )
