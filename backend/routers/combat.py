"""Combat endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Request

from auth import User
from dependencies import get_optional_user, limiter, RATE_LIMIT_GAME
from game_engine import get_game_engine_for_session
from session_manager import get_session_id_for_user
from schemas import ActionResponse

router = APIRouter(prefix="/api/game/combat", tags=["Combat"])


@router.post(
    "/attack",
    response_model=ActionResponse,
    summary="Attack enemy",
    description="""
Attack the current enemy in combat. Only works when in an active combat encounter.

Returns combat results including damage dealt, enemy response, and victory/defeat status.
    """
)
@limiter.limit(RATE_LIMIT_GAME)
async def attack(request: Request, current_user: Optional[User] = Depends(get_optional_user)):
    """Attack the current enemy in combat."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)
    result = await engine.attack()

    return ActionResponse(
        success=result.success,
        message=result.message,
        narrative=result.narrative,
        state=engine.get_game_state(),
        combat=result.combat_data
    )


@router.post(
    "/flee",
    response_model=ActionResponse,
    summary="Flee from combat",
    description="""
Attempt to flee from the current combat encounter.

Success is based on player speed vs enemy speed. Failed flee attempts may result in
taking damage. Returns to exploration mode on success.
    """
)
@limiter.limit(RATE_LIMIT_GAME)
async def flee(request: Request, current_user: Optional[User] = Depends(get_optional_user)):
    """Attempt to flee from combat."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)
    result = await engine.flee()

    return ActionResponse(
        success=result.success,
        message=result.message,
        narrative=result.narrative,
        state=engine.get_game_state(),
        combat=result.combat_data
    )
