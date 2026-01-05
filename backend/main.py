"""
Tile-Crawler Backend API

FastAPI application providing endpoints for the dungeon crawler game.
"""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from game_engine import get_game_engine, reset_game_engine
from llm_engine import get_llm_engine

load_dotenv()


# Request/Response Models
class NewGameRequest(BaseModel):
    player_name: str = "Adventurer"


class MoveRequest(BaseModel):
    direction: str  # north, south, east, west, up, down


class TakeItemRequest(BaseModel):
    item_id: str


class UseItemRequest(BaseModel):
    item_id: str


class TalkRequest(BaseModel):
    message: str = ""


class ActionResponse(BaseModel):
    success: bool
    message: str
    narrative: str = ""
    map: Optional[list[str]] = None
    state: Optional[dict] = None
    combat: Optional[dict] = None
    dialogue: Optional[dict] = None


class GameStateResponse(BaseModel):
    player: dict
    position: list[int]
    room: dict
    inventory: list[dict]
    gold: int
    combat: Optional[dict]
    narrative: dict
    stats: dict


class HealthResponse(BaseModel):
    status: str
    llm_available: bool
    version: str


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    print("🎮 Tile-Crawler Backend Starting...")
    print(f"   LLM Available: {get_llm_engine().is_available()}")
    yield
    # Shutdown
    print("🎮 Tile-Crawler Backend Shutting Down...")


# Create FastAPI app
app = FastAPI(
    title="Tile-Crawler API",
    description="Backend API for the LLM-powered dungeon crawler",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health & Status Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint."""
    return HealthResponse(
        status="online",
        llm_available=get_llm_engine().is_available(),
        version="0.1.0"
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check."""
    return HealthResponse(
        status="healthy",
        llm_available=get_llm_engine().is_available(),
        version="0.1.0"
    )


# Game Management Endpoints
@app.post("/api/game/new", response_model=ActionResponse)
async def new_game(request: NewGameRequest):
    """Start a new game."""
    try:
        engine = reset_game_engine()
        result = await engine.new_game(request.player_name)

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            map=result.map_update,
            state=engine.get_game_state()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/game/state", response_model=GameStateResponse)
async def get_game_state():
    """Get current game state."""
    try:
        engine = get_game_engine()
        state = engine.get_game_state()
        return GameStateResponse(**state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game/save")
async def save_game():
    """Save the current game state."""
    try:
        engine = get_game_engine()
        engine._save_all()
        return {"success": True, "message": "Game saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game/load")
async def load_game():
    """Load saved game state."""
    try:
        # Reset engine to reload from saved files
        engine = reset_game_engine()
        state = engine.get_game_state()
        return {
            "success": True,
            "message": "Game loaded successfully",
            "state": state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Movement Endpoints
@app.post("/api/game/move", response_model=ActionResponse)
async def move(request: MoveRequest):
    """Move the player in a direction."""
    valid_directions = ["north", "south", "east", "west", "up", "down"]
    if request.direction.lower() not in valid_directions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid direction. Must be one of: {valid_directions}"
        )

    try:
        engine = get_game_engine()
        result = await engine.move(request.direction.lower())

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            map=result.map_update,
            state=engine.get_game_state(),
            combat=result.combat_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Shorthand movement endpoints
@app.post("/api/game/move/north", response_model=ActionResponse)
async def move_north():
    """Move north."""
    return await move(MoveRequest(direction="north"))


@app.post("/api/game/move/south", response_model=ActionResponse)
async def move_south():
    """Move south."""
    return await move(MoveRequest(direction="south"))


@app.post("/api/game/move/east", response_model=ActionResponse)
async def move_east():
    """Move east."""
    return await move(MoveRequest(direction="east"))


@app.post("/api/game/move/west", response_model=ActionResponse)
async def move_west():
    """Move west."""
    return await move(MoveRequest(direction="west"))


# Combat Endpoints
@app.post("/api/game/combat/attack", response_model=ActionResponse)
async def attack():
    """Attack the current enemy."""
    try:
        engine = get_game_engine()
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


@app.post("/api/game/combat/flee", response_model=ActionResponse)
async def flee():
    """Attempt to flee from combat."""
    try:
        engine = get_game_engine()
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


# Inventory Endpoints
@app.post("/api/game/take", response_model=ActionResponse)
async def take_item(request: TakeItemRequest):
    """Pick up an item from the current room."""
    try:
        engine = get_game_engine()
        result = await engine.take_item(request.item_id)

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game/use", response_model=ActionResponse)
async def use_item(request: UseItemRequest):
    """Use an item from inventory."""
    try:
        engine = get_game_engine()
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


@app.get("/api/game/inventory")
async def get_inventory():
    """Get the player's inventory."""
    try:
        engine = get_game_engine()
        state = engine.get_game_state()
        return {
            "inventory": state["inventory"],
            "gold": state["gold"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Interaction Endpoints
@app.post("/api/game/talk", response_model=ActionResponse)
async def talk(request: TalkRequest):
    """Talk to an NPC in the current room."""
    try:
        engine = get_game_engine()
        result = await engine.talk(request.message)

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            dialogue=result.dialogue_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game/rest", response_model=ActionResponse)
async def rest():
    """Rest to recover HP and mana (only in safe rooms)."""
    try:
        engine = get_game_engine()
        result = engine.rest()

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Generic action endpoint for flexibility
@app.post("/api/game/action", response_model=ActionResponse)
async def perform_action(action: str, target: Optional[str] = None):
    """
    Perform a generic game action.

    Actions: move, attack, flee, take, use, talk, rest
    """
    engine = get_game_engine()

    try:
        if action == "move" and target:
            result = await engine.move(target)
        elif action == "attack":
            result = await engine.attack()
        elif action == "flee":
            result = await engine.flee()
        elif action == "take" and target:
            result = await engine.take_item(target)
        elif action == "use" and target:
            result = await engine.use_item(target)
        elif action == "talk":
            result = await engine.talk(target or "")
        elif action == "rest":
            result = engine.rest()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action: {action}"
            )

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            map=result.map_update,
            state=engine.get_game_state(),
            combat=result.combat_data,
            dialogue=result.dialogue_data
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug
    )
