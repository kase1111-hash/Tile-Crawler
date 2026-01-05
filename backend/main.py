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
from audio_engine import get_audio_engine

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
    audio: Optional[dict] = None  # Audio intent for TTS synthesis


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
        audio_engine = get_audio_engine()
        result = await engine.new_game(request.player_name)

        # Generate room enter audio
        state = engine.get_game_state()
        biome = state.get("room", {}).get("biome", "dungeon")
        audio_engine.set_biome(biome)
        audio_batch = audio_engine.generate_room_enter_audio()

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            map=result.map_update,
            state=state,
            audio=audio_batch.model_dump() if audio_batch else None
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
        audio_engine = get_audio_engine()
        result = await engine.move(request.direction.lower())

        # Generate audio based on result
        state = engine.get_game_state()
        audio_data = None

        if result.success:
            biome = state.get("room", {}).get("biome", "dungeon")
            audio_engine.set_biome(biome)

            # Check if entering combat
            if result.combat_data and result.combat_data.get("active"):
                enemy_name = result.combat_data.get("enemy", {}).get("name", "enemy")
                if result.combat_data.get("enemy", {}).get("is_boss"):
                    audio_data = audio_engine.generate_boss_intro_audio(enemy_name).model_dump()
                else:
                    audio_engine.set_combat_state(True)
                    audio_data = audio_engine.generate_room_enter_audio().model_dump()
            else:
                # Normal room enter
                audio_data = audio_engine.generate_room_enter_audio().model_dump()
        else:
            # Blocked movement
            audio_data = audio_engine.generate_ui_audio("error").model_dump()

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            map=result.map_update,
            state=state,
            combat=result.combat_data,
            audio=audio_data
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
        audio_engine = get_audio_engine()
        result = await engine.attack()

        # Generate combat audio
        audio_data = None
        if result.combat_data:
            combat = result.combat_data
            if combat.get("player_hit"):
                damage = combat.get("player_damage", 0)
                critical = combat.get("critical", False)
                audio_batch = audio_engine.generate_attack_audio(
                    weapon_type="sword",
                    hit=True,
                    damage=damage,
                    critical=critical
                )
                audio_data = audio_batch.model_dump()

                # Check for enemy death
                if not combat.get("active") and combat.get("victory"):
                    enemy_name = combat.get("enemy", {}).get("name", "enemy")
                    audio_data = audio_engine.generate_enemy_death_audio(enemy_name).model_dump()
            else:
                audio_batch = audio_engine.generate_attack_audio(hit=False)
                audio_data = audio_batch.model_dump()

            # Check for player taking damage
            if combat.get("enemy_hit"):
                state = engine.get_game_state()
                player = state.get("player", {})
                hurt_audio = audio_engine.generate_player_hurt_audio(
                    combat.get("enemy_damage", 0),
                    player.get("hp", 50),
                    player.get("max_hp", 100)
                )
                # Layer the hurt sound
                if audio_data:
                    audio_data["layers"] = [hurt_audio.primary.model_dump()]

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            combat=result.combat_data,
            audio=audio_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game/combat/flee", response_model=ActionResponse)
async def flee():
    """Attempt to flee from combat."""
    try:
        engine = get_game_engine()
        audio_engine = get_audio_engine()
        result = await engine.flee()

        # Generate flee audio
        audio_data = None
        if result.success:
            audio_intent = audio_engine.generate_movement_audio("stone")
            audio_data = {"primary": audio_intent.model_dump()}
            audio_engine.set_combat_state(False)
        elif result.combat_data and result.combat_data.get("active"):
            # Failed to flee while in combat
            state = engine.get_game_state()
            player = state.get("player", {})
            hurt_batch = audio_engine.generate_player_hurt_audio(
                5, player.get("hp", 50), player.get("max_hp", 100)
            )
            audio_data = hurt_batch.model_dump()
        else:
            # Not in combat - just play error
            audio_intent = audio_engine.generate_ui_audio("error")
            audio_data = {"primary": audio_intent.model_dump()}

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            combat=result.combat_data,
            audio=audio_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Inventory Endpoints
@app.post("/api/game/take", response_model=ActionResponse)
async def take_item(request: TakeItemRequest):
    """Pick up an item from the current room."""
    try:
        engine = get_game_engine()
        audio_engine = get_audio_engine()
        result = await engine.take_item(request.item_id)

        # Generate pickup audio
        if result.success:
            item_type = "gold" if "gold" in request.item_id.lower() else "item"
            audio_intent = audio_engine.generate_pickup_audio(item_type)
            audio_data = {"primary": audio_intent.model_dump()}
        else:
            audio_intent = audio_engine.generate_ui_audio("error")
            audio_data = {"primary": audio_intent.model_dump()}

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            audio=audio_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game/use", response_model=ActionResponse)
async def use_item(request: UseItemRequest):
    """Use an item from inventory."""
    try:
        engine = get_game_engine()
        audio_engine = get_audio_engine()
        result = await engine.use_item(request.item_id)

        # Generate use audio based on item type
        audio_data = None
        if result.success:
            item_id = request.item_id.lower()
            if "potion" in item_id or "elixir" in item_id:
                audio_intent = audio_engine.generate_potion_audio()
                audio_data = {"primary": audio_intent.model_dump()}
            elif "scroll" in item_id:
                audio_batch = audio_engine.generate_discovery_audio("scroll")
                audio_data = audio_batch.model_dump()
            else:
                audio_intent = audio_engine.generate_equip_audio()
                audio_data = {"primary": audio_intent.model_dump()}
        else:
            audio_intent = audio_engine.generate_ui_audio("error")
            audio_data = {"primary": audio_intent.model_dump()}

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            combat=result.combat_data,
            audio=audio_data
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
        audio_engine = get_audio_engine()
        result = await engine.talk(request.message)

        # Generate NPC audio based on dialogue mood
        audio_data = None
        if result.success and result.dialogue_data:
            mood = result.dialogue_data.get("mood", "friendly")
            audio_intent = audio_engine.generate_npc_reaction_audio(mood)
            audio_data = {"primary": audio_intent.model_dump()}

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            dialogue=result.dialogue_data,
            audio=audio_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game/rest", response_model=ActionResponse)
async def rest():
    """Rest to recover HP and mana (only in safe rooms)."""
    try:
        engine = get_game_engine()
        audio_engine = get_audio_engine()
        result = engine.rest()

        # Generate rest audio
        if result.success:
            # Peaceful ambient for resting
            from audio_engine import AudioIntent
            rest_intent = AudioIntent(
                event_type="ambient",
                onomatopoeia="zzzzz... ahhh...",
                emotion="peaceful",
                intensity=0.4,
                pitch_shift=-2,
                speed=0.7,
                reverb=0.5,
                style="ambient_drone",
                loop=False,
                priority=3
            )
            audio_data = {"primary": rest_intent.model_dump()}
        else:
            audio_intent = audio_engine.generate_ui_audio("error")
            audio_data = {"primary": audio_intent.model_dump()}

        return ActionResponse(
            success=result.success,
            message=result.message,
            narrative=result.narrative,
            state=engine.get_game_state(),
            audio=audio_data
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
