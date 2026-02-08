"""Interaction endpoints (talk, rest)."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from auth import User
from dependencies import get_optional_user
from game_engine import get_game_engine_for_session
from session_manager import get_session_id_for_user
from schemas import TalkRequest, ActionResponse

router = APIRouter(prefix="/api/game", tags=["Interaction"])


@router.post(
    "/talk",
    response_model=ActionResponse,
    summary="Talk to NPC",
    description="""Initiate conversation with an NPC in the current room.

The LLM generates contextual dialogue responses based on:
- NPC personality and role
- Current game state
- Previous interactions
- Player's message content"""
)
async def talk(
    talk_request: TalkRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Talk to an NPC in the current room."""
    try:
        session_id = get_session_id_for_user(
            current_user.id if current_user else None
        )
        engine = await get_game_engine_for_session(session_id)
        result = await engine.talk(talk_request.message)

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            dialogue=result.dialogue_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/rest",
    response_model=ActionResponse,
    summary="Rest and recover",
    description="""Rest to recover HP and mana.

**Requirements:**
- Must be in a safe room (no enemies present)
- Cannot rest during combat"""
)
async def rest(current_user: Optional[User] = Depends(get_optional_user)):
    """Rest to recover HP and mana (only in safe rooms)."""
    try:
        session_id = get_session_id_for_user(
            current_user.id if current_user else None
        )
        engine = await get_game_engine_for_session(session_id)
        result = await engine.rest()

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
