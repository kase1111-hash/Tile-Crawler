"""Combat endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from auth import User
from dependencies import get_optional_user
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
async def attack(current_user: Optional[User] = Depends(get_optional_user)):
    """Attack the current enemy in combat."""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
async def flee(current_user: Optional[User] = Depends(get_optional_user)):
    """Attempt to flee from combat."""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
