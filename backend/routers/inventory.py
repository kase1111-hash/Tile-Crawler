"""Inventory endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from auth import User
from dependencies import get_optional_user
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
async def take_item(
    request: TakeItemRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Pick up an item from the current room."""
    try:
        session_id = get_session_id_for_user(
            current_user.id if current_user else None
        )
        engine = await get_game_engine_for_session(session_id)
        result = await engine.take_item(request.item_id)

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
async def use_item(
    request: UseItemRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Use an item from inventory."""
    try:
        session_id = get_session_id_for_user(
            current_user.id if current_user else None
        )
        engine = await get_game_engine_for_session(session_id)
        result = await engine.use_item(request.item_id)

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            combat=result.combat_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/inventory",
    response_model=InventoryResponse,
    summary="Get inventory",
    description="Retrieve the player's current inventory items and gold count."
)
async def get_inventory(
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get the player's inventory."""
    try:
        session_id = get_session_id_for_user(
            current_user.id if current_user else None
        )
        engine = await get_game_engine_for_session(session_id)
        state = engine.get_game_state()
        return {
            "inventory": state["inventory"],
            "gold": state["gold"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
