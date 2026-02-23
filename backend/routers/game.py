"""Game management and movement endpoints."""

from typing import Optional

from fastapi import APIRouter, Query, Depends, Request

from auth import User
from dependencies import get_optional_user, AUTH_ENABLED, limiter, RATE_LIMIT_GAME
from game_engine import get_game_engine_for_session, reset_game_engine_for_session
from session_manager import get_session_id_for_user
from auth import get_auth_service
from schemas import (
    NewGameRequest, MoveRequest, ActionResponse,
    GameStateResponse, SaveLoadResponse,
)

router = APIRouter(prefix="/api/game")


@router.post(
    "/new",
    response_model=ActionResponse,
    tags=["Game Management"],
    summary="Start a new game",
    description="""
Start a new game session with the specified player name.

This resets all game state and generates the starting room.
Returns the initial game state including map and player stats.
    """
)
@limiter.limit(RATE_LIMIT_GAME)
async def new_game(
    request: Request,
    game_request: NewGameRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Start a new game session."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )

    engine = await reset_game_engine_for_session(session_id)
    result = await engine.new_game(game_request.player_name)

    state = engine.get_game_state()

    return ActionResponse(
        success=result.success,
        message=result.message,
        narrative=result.narrative,
        map=result.map_update,
        state=state
    )


@router.get(
    "/state",
    response_model=GameStateResponse,
    tags=["Game Management"],
    summary="Get current game state",
    description="Retrieve the complete current game state including player, room, inventory, and stats."
)
@limiter.limit(RATE_LIMIT_GAME)
async def get_game_state(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get the current game state."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)

    # Ensure room exists at current position
    x, y, z = engine.world.current_position
    if not engine.world.room_exists(x, y, z):
        biome = engine._determine_biome(z)
        exits = {"south": True} if (x, y, z) == (0, 0, 0) else engine._determine_exits(x, y, z, "north")
        await engine._generate_room(x, y, z, biome, exits)

    state = engine.get_game_state()
    return GameStateResponse(**state)


@router.post(
    "/save",
    response_model=SaveLoadResponse,
    tags=["Game Management"],
    summary="Save game",
    description="""Save the current game state to database.

If authenticated, saves are linked to your user account.
Anonymous saves use 'anonymous' as player_id."""
)
@limiter.limit(RATE_LIMIT_GAME)
async def save_game(
    request: Request,
    save_name: str = Query(default="quicksave", description="Name for the save slot"),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Save the current game state to database."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)

    player_id = f"user_{current_user.id}" if current_user else "anonymous"

    save_id = engine.save_to_database(player_id, save_name)

    if current_user and AUTH_ENABLED:
        auth_service = get_auth_service()
        auth_service.increment_games_played(current_user.id)

    return SaveLoadResponse(
        success=True,
        message=f"Game saved successfully (ID: {save_id})"
    )


@router.post(
    "/load",
    response_model=SaveLoadResponse,
    tags=["Game Management"],
    summary="Load game",
    description="""Load a previously saved game state from database.

If save_id is not specified, loads the most recent save."""
)
@limiter.limit(RATE_LIMIT_GAME)
async def load_game(
    request: Request,
    save_id: Optional[int] = Query(default=None, description="Specific save ID to load"),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Load saved game state from database."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)

    player_id = f"user_{current_user.id}" if current_user else "anonymous"

    success = engine.load_from_database(save_id, player_id)

    if not success:
        return SaveLoadResponse(
            success=False,
            message="No saved game found"
        )

    state = engine.get_game_state()
    return SaveLoadResponse(
        success=True,
        message="Game loaded successfully",
        state=state
    )


@router.get(
    "/saves",
    tags=["Game Management"],
    summary="List saves",
    description="List all saved games for the current user."
)
@limiter.limit(RATE_LIMIT_GAME)
async def list_saves(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """List all saves for the current user."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)

    player_id = f"user_{current_user.id}" if current_user else "anonymous"

    saves = engine.list_saves(player_id)
    return {
        "success": True,
        "saves": saves,
        "count": len(saves),
        "user": current_user.username if current_user else "anonymous"
    }


@router.post(
    "/move",
    response_model=ActionResponse,
    tags=["Movement"],
    summary="Move player",
    description="""
Move the player in a cardinal direction (north, south, east, west) or vertically (up, down).

Returns success/failure, narrative description, and updated map.
May trigger combat if entering a room with enemies.
    """
)
@limiter.limit(RATE_LIMIT_GAME)
async def move(
    request: Request,
    move_request: MoveRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Move the player in a direction."""
    session_id = get_session_id_for_user(
        current_user.id if current_user else None
    )
    engine = await get_game_engine_for_session(session_id)
    result = await engine.move(move_request.direction.lower())

    state = engine.get_game_state()

    return ActionResponse(
        success=result.success,
        message=result.message,
        narrative=result.narrative,
        map=result.map_update,
        state=state,
        combat=result.combat_data
    )


@router.post(
    "/prefetch",
    tags=["Game Management"],
    summary="Prefetch adjacent rooms",
    description="""Pre-generate rooms for all available exits.

This improves perceived performance by generating rooms in the background
while the player is viewing the current room."""
)
@limiter.limit(RATE_LIMIT_GAME)
async def prefetch(request: Request, current_user: Optional[User] = Depends(get_optional_user)):
    """Prefetch adjacent rooms for faster navigation."""
    try:
        session_id = get_session_id_for_user(
            current_user.id if current_user else None
        )
        engine = await get_game_engine_for_session(session_id)
        results = await engine.prefetch_adjacent_rooms()
        return {"success": True, "prefetched": results}
    except Exception:
        return {"success": False, "error": "Prefetch failed"}
