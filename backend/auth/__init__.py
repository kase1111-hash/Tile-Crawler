"""
Authentication package for Tile-Crawler

Provides user authentication with:
- JWT token-based authentication
- Password hashing with bcrypt
- User registration and login
- Per-user game save isolation
"""

from .models import User, UserCreate, UserLogin, Token, TokenData
from .service import AuthService, get_auth_service
from .dependencies import get_current_user, get_current_user_optional

__all__ = [
    "User",
    "UserCreate",
    "UserLogin",
    "Token",
    "TokenData",
    "AuthService",
    "get_auth_service",
    "get_current_user",
    "get_current_user_optional",
]
