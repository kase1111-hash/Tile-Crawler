"""Inventory endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Request

from auth import User
from dependencies import get_optional_user, limiter, RATE_LIMIT_GAME
from game_engine import get_game_engine_for_session
from session_manager import get_session_id_for_user
from schemas import TakeItemRequest, UseItemRequest, ActionResponse, InventoryResponse

router = APIRouter(prefix="/api/game", tags=["Inventory"])


@router.post(
    "/take",
    response_model=ActionResponse,
    summary="Take item",
    description="Pick up an item from the current room and add it to inventory."
)
@limiter.limit(RATE_LIMIT_GAME)
async def take_item(
    request: Request,
    item_request: TakeItemRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Pick up an item from the current room."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)
    result = await engine.take_item(item_request.item_id)

    return ActionResponse(
        success=result.success,
        message=result.message,
        narrative=result.narrative,
        state=engine.get_game_state()
    )


@router.post(
    "/use",
    response_model=ActionResponse,
    summary="Use item",
    description="""Use an item from the player's inventory.

Different item types produce different effects:
- **Potions/Elixirs**: Restore HP or provide buffs
- **Scrolls**: Cast magical effects
- **Equipment**: Equip weapons or armor"""
)
@limiter.limit(RATE_LIMIT_GAME)
async def use_item(
    request: Request,
    item_request: UseItemRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Use an item from inventory."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)
    result = await engine.use_item(item_request.item_id)

    return ActionResponse(
        success=result.success,
        message=result.message,
        narrative=result.narrative,
        state=engine.get_game_state(),
        combat=result.combat_data
    )


@router.get(
    "/inventory",
    response_model=InventoryResponse,
    summary="Get inventory",
    description="Retrieve the player's current inventory items and gold count."
)
@limiter.limit(RATE_LIMIT_GAME)
async def get_inventory(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get the player's inventory."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)
    state = engine.get_game_state()
    return {
        "inventory": state["inventory"],
        "gold": state["gold"]
    }
