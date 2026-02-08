"""Authentication endpoints (only active when AUTH_ENABLED=true)."""

from fastapi import APIRouter, HTTPException, Depends, Request

from auth import (
    User, UserCreate, UserLogin, Token,
    get_auth_service, get_current_user,
)
from dependencies import limiter, RATE_LIMIT_AUTH
from game_engine import get_game_engine_for_session
from session_manager import get_session_id_for_user
from schemas import ChangePasswordRequest

router = APIRouter(tags=["Authentication"])


@router.post(
    "/api/auth/register",
    response_model=Token,
    summary="Register new user",
    description="""Create a new user account.

Username must be 3-50 characters, alphanumeric with underscores/hyphens.
Password must be at least 6 characters.
Returns a JWT token for immediate login."""
)
@limiter.limit(RATE_LIMIT_AUTH)
async def register(request: Request, user_data: UserCreate):
    """Register a new user and return auth token."""
    auth_service = get_auth_service()
    user = auth_service.register(user_data)

    if user is None:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )

    token = auth_service.login(user_data.username, user_data.password)
    return token


@router.post(
    "/api/auth/login",
    response_model=Token,
    summary="Login",
    description="Authenticate with username and password to receive a JWT token."
)
@limiter.limit(RATE_LIMIT_AUTH)
async def login(request: Request, credentials: UserLogin):
    """Login and receive JWT token."""
    auth_service = get_auth_service()
    token = auth_service.login(credentials.username, credentials.password)

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    return token


@router.get(
    "/api/auth/me",
    response_model=User,
    summary="Get current user",
    description="Get the profile of the currently authenticated user."
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.post(
    "/api/auth/change-password",
    summary="Change password",
    description="Change the password for the current user."
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """Change current user's password."""
    auth_service = get_auth_service()
    success = auth_service.change_password(
        current_user.id,
        request.old_password,
        request.new_password
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    return {"success": True, "message": "Password changed successfully"}


@router.delete(
    "/api/game/saves/{save_id}",
    tags=["Game Management"],
    summary="Delete save",
    description="""Delete a specific saved game by ID.

**Authentication:** Required. You can only delete your own saves."""
)
async def delete_save(
    save_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a saved game (requires authentication)."""
    try:
        session_id = get_session_id_for_user(current_user.id)
        engine = await get_game_engine_for_session(session_id)

        from database import get_repository
        repo = get_repository()
        save = repo.load_game(save_id)

        if save is None:
            raise HTTPException(status_code=404, detail="Save not found")

        expected_player_id = f"user_{current_user.id}"
        if save.player_id != expected_player_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to delete this save"
            )

        success = engine.delete_save(save_id)
        return {
            "success": success,
            "message": "Save deleted" if success else "Save not found"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
