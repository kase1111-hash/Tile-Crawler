"""
Authentication models for Tile-Crawler

Pydantic models for user authentication and authorization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    """Base user model with common fields."""
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, underscores, hyphens)"
    )
    email: Optional[str] = Field(
        default=None,
        description="Optional email address"
    )


class UserCreate(UserBase):
    """Model for user registration."""
    password: str = Field(
        min_length=6,
        max_length=100,
        description="Password (min 6 characters)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "username": "adventurer",
                "email": "adventurer@example.com",
                "password": "secret123"
            }
        }


class UserLogin(BaseModel):
    """Model for user login."""
    username: str = Field(description="Username")
    password: str = Field(description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "adventurer",
                "password": "secret123"
            }
        }


class User(UserBase):
    """Full user model (without password)."""
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    total_playtime: int = 0  # Total playtime in seconds
    games_played: int = 0

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "adventurer",
                "email": "adventurer@example.com",
                "created_at": "2024-01-01T00:00:00",
                "last_login": "2024-01-02T12:00:00",
                "is_active": True,
                "total_playtime": 3600,
                "games_played": 5
            }
        }


class UserInDB(User):
    """User model with hashed password (for internal use)."""
    hashed_password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration in seconds")
    user: User

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "id": 1,
                    "username": "adventurer",
                    "email": "adventurer@example.com"
                }
            }
        }


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: int
    username: str
    exp: datetime
