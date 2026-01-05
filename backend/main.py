"""
Tile-Crawler Backend API

FastAPI application providing endpoints for the dungeon crawler game.
"""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

from game_engine import get_game_engine, reset_game_engine
from llm_engine import get_llm_engine
from audio_engine import get_audio_engine
from websocket_manager import get_websocket_manager
from auth import (
    AuthService, get_auth_service, User, UserCreate, UserLogin, Token,
    get_current_user, get_current_user_optional
)

load_dotenv()


# =============================================================================
# Request/Response Models with OpenAPI Documentation
# =============================================================================

class NewGameRequest(BaseModel):
    """Request to start a new game session."""
    model_config = ConfigDict(json_schema_extra={"example": {"player_name": "Brave Hero"}})

    player_name: str = Field(
        default="Adventurer",
        description="The name of the player character",
        min_length=1,
        max_length=50,
        json_schema_extra={"example": "Brave Hero"}
    )


class MoveRequest(BaseModel):
    """Request to move the player in a direction."""
    model_config = ConfigDict(json_schema_extra={"example": {"direction": "north"}})

    direction: str = Field(
        description="Direction to move: north, south, east, west, up, or down",
        json_schema_extra={"example": "north"}
    )


class TakeItemRequest(BaseModel):
    """Request to pick up an item from the current room."""
    model_config = ConfigDict(json_schema_extra={"example": {"item_id": "healing_potion"}})

    item_id: str = Field(
        description="The unique identifier of the item to pick up",
        json_schema_extra={"example": "rusty_sword"}
    )


class UseItemRequest(BaseModel):
    """Request to use an item from inventory."""
    model_config = ConfigDict(json_schema_extra={"example": {"item_id": "healing_potion"}})

    item_id: str = Field(
        description="The unique identifier of the item to use",
        json_schema_extra={"example": "healing_potion"}
    )


class TalkRequest(BaseModel):
    """Request to talk to an NPC."""
    model_config = ConfigDict(json_schema_extra={"example": {"message": "Hello, what news do you have?"}})

    message: str = Field(
        default="",
        description="Optional message to say to the NPC",
        json_schema_extra={"example": "Hello, what news do you have?"}
    )


class AudioIntentResponse(BaseModel):
    """TTS audio synthesis intent for procedural sound generation."""
    event_type: str = Field(description="Type of audio: sfx, ambient, music_motif, ui_feedback, dialogue")
    onomatopoeia: str = Field(description="Comic-style sound text to synthesize (e.g., 'KRAKOOM!')")
    emotion: str = Field(description="Emotional tone: neutral, tense, triumphant, mysterious, danger, peaceful")
    intensity: float = Field(description="Sound intensity from 0.0 to 1.0")
    pitch_shift: float = Field(description="Pitch adjustment in semitones (-12 to +12)")
    speed: float = Field(description="Playback speed multiplier (0.5 to 2.0)")
    reverb: float = Field(description="Reverb amount from 0.0 to 1.0")
    style: str = Field(description="Audio style: comic_noir, fantasy_epic, horror_whisper, retro_8bit")
    loop: bool = Field(description="Whether the sound should loop")
    priority: int = Field(description="Priority level 1-10, higher = more important")


class ActionResponse(BaseModel):
    """Standard response for game actions."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "You move north into a dark corridor.",
            "narrative": "The ancient stones crumble beneath your feet as you venture deeper into the dungeon.",
            "audio": {"primary": {"event_type": "sfx", "onomatopoeia": "CREEEAK... thud", "emotion": "mysterious", "intensity": 0.6}}
        }
    })

    success: bool = Field(description="Whether the action was successful")
    message: str = Field(description="Human-readable result message")
    narrative: str = Field(default="", description="LLM-generated narrative text")
    map: Optional[list[str]] = Field(default=None, description="ASCII map of current room (11x15 grid)")
    state: Optional[dict] = Field(default=None, description="Full game state snapshot")
    combat: Optional[dict] = Field(default=None, description="Combat state if in battle")
    dialogue: Optional[dict] = Field(default=None, description="NPC dialogue data if talking")
    audio: Optional[dict] = Field(default=None, description="TTS audio intent for sound synthesis")


class GameStateResponse(BaseModel):
    """Complete game state snapshot."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "player": {"name": "Brave Hero", "level": 1, "hp": "100/100", "mana": "50/50", "attack": 10, "defense": 5},
            "position": [0, 0, 1],
            "room": {"biome": "dungeon", "description": "A cold stone chamber...", "exits": {"north": True, "south": False, "east": True, "west": False}},
            "inventory": [{"id": "torch", "name": "Torch", "quantity": 1}],
            "gold": 20, "combat": None,
            "narrative": {"story_summary": "A brave adventurer enters the dungeon..."},
            "stats": {"rooms_explored": 1, "enemies_defeated": 0}
        }
    })

    player: dict = Field(description="Player stats including HP, level, attributes")
    position: list[int] = Field(description="Current [x, y, z] coordinates")
    room: dict = Field(description="Current room data including map, enemies, items")
    inventory: list[dict] = Field(description="List of items in player's inventory")
    gold: int = Field(description="Amount of gold the player has")
    combat: Optional[dict] = Field(default=None, description="Combat state if currently in battle")
    narrative: dict = Field(description="Narrative context and recent events")
    stats: dict = Field(description="Game statistics (rooms explored, enemies defeated, etc.)")


class HealthResponse(BaseModel):
    """API health check response."""
    model_config = ConfigDict(json_schema_extra={"example": {"status": "healthy", "llm_available": True, "version": "0.1.0"}})

    status: str = Field(description="Service status: online, healthy, degraded")
    llm_available: bool = Field(description="Whether the LLM engine is available")
    version: str = Field(description="API version string")


class InventoryResponse(BaseModel):
    """Player inventory response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "inventory": [{"id": "torch", "name": "Torch", "category": "tool", "quantity": 1}, {"id": "healing_potion", "name": "Healing Potion", "category": "consumable", "quantity": 2}],
            "gold": 20
        }
    })

    inventory: list[dict] = Field(description="List of inventory items")
    gold: int = Field(description="Current gold amount")


class SaveLoadResponse(BaseModel):
    """Response for save/load operations."""
    model_config = ConfigDict(json_schema_extra={"example": {"success": True, "message": "Game saved successfully", "state": None}})

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Result message")
    state: Optional[dict] = Field(default=None, description="Game state (for load operations)")


# =============================================================================
# API Tags for Documentation Organization
# =============================================================================

tags_metadata = [
    {
        "name": "Authentication",
        "description": "User registration, login, and profile management",
    },
    {
        "name": "Health",
        "description": "API health and status endpoints",
    },
    {
        "name": "Game Management",
        "description": "Start, save, and load game sessions",
    },
    {
        "name": "Movement",
        "description": "Move the player through the dungeon",
    },
    {
        "name": "Combat",
        "description": "Combat actions when fighting enemies",
    },
    {
        "name": "Inventory",
        "description": "Manage player inventory and items",
    },
    {
        "name": "Interaction",
        "description": "Interact with NPCs and the environment",
    },
    {
        "name": "WebSocket",
        "description": "Real-time game updates via WebSocket connection",
    },
]


# =============================================================================
# Application Setup
# =============================================================================

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    print("🎮 Tile-Crawler Backend Starting...")
    print(f"   LLM Available: {get_llm_engine().is_available()}")
    yield
    print("🎮 Tile-Crawler Backend Shutting Down...")


# Create FastAPI app with enhanced documentation
app = FastAPI(
    title="Tile-Crawler API",
    description="""
# Tile-Crawler Backend API

An LLM-powered procedural dungeon crawler with TTS-based audio synthesis.

## Features

- **Procedural Generation**: Rooms, narratives, and encounters generated by LLM
- **Turn-Based Combat**: Fight enemies in strategic turn-based battles
- **TTS Audio**: Procedural sound effects via text-to-speech synthesis
- **Persistent State**: Save and load your progress

## Quick Start

1. **Start a new game**: `POST /api/game/new`
2. **Explore**: `POST /api/game/move` with direction
3. **Check inventory**: `GET /api/game/inventory`
4. **Fight enemies**: `POST /api/game/combat/attack`
5. **Save progress**: `POST /api/game/save`

## Audio System

The API returns `audio` intents with comic-book style onomatopoeia (KRAKOOM!, WHOOSH!)
that can be synthesized using TTS and processed with Web Audio API effects.
    """,
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Tile-Crawler",
        "url": "https://github.com/kase1111-hash/Tile-Crawler",
    },
    license_info={
        "name": "MIT",
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.post(
    "/api/auth/register",
    response_model=Token,
    tags=["Authentication"],
    summary="Register new user",
    description="""Create a new user account.

Username must be 3-50 characters, alphanumeric with underscores/hyphens.
Password must be at least 6 characters.
Returns a JWT token for immediate login."""
)
async def register(user_data: UserCreate):
    """Register a new user and return auth token."""
    auth_service = get_auth_service()
    user = auth_service.register(user_data)

    if user is None:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists"
        )

    # Auto-login after registration
    token = auth_service.login(user_data.username, user_data.password)
    return token


@app.post(
    "/api/auth/login",
    response_model=Token,
    tags=["Authentication"],
    summary="Login",
    description="Authenticate with username and password to receive a JWT token."
)
async def login(credentials: UserLogin):
    """Login and receive JWT token."""
    auth_service = get_auth_service()
    token = auth_service.login(credentials.username, credentials.password)

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    return token


@app.get(
    "/api/auth/me",
    response_model=User,
    tags=["Authentication"],
    summary="Get current user",
    description="Get the profile of the currently authenticated user."
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@app.post(
    "/api/auth/change-password",
    tags=["Authentication"],
    summary="Change password",
    description="Change the password for the current user."
)
async def change_password(
    old_password: str = Query(description="Current password"),
    new_password: str = Query(min_length=6, description="New password"),
    current_user: User = Depends(get_current_user)
):
    """Change current user's password."""
    auth_service = get_auth_service()
    success = auth_service.change_password(
        current_user.id,
        old_password,
        new_password
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    return {"success": True, "message": "Password changed successfully"}


# =============================================================================
# Health & Status Endpoints
# =============================================================================

@app.get(
    "/",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Root health check",
    description="Quick health check endpoint returning API status."
)
async def root():
    """Root endpoint - returns basic health status."""
    return HealthResponse(
        status="online",
        llm_available=get_llm_engine().is_available(),
        version="0.1.0"
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Detailed health check including LLM availability status."
)
async def health_check_root():
    """Detailed health check at /health."""
    return HealthResponse(
        status="healthy",
        llm_available=get_llm_engine().is_available(),
        version="0.1.0"
    )


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="API health check",
    description="Detailed health check including LLM availability status."
)
async def health_check():
    """Detailed health check at /api/health."""
    return HealthResponse(
        status="healthy",
        llm_available=get_llm_engine().is_available(),
        version="0.1.0"
    )


# =============================================================================
# Game Management Endpoints
# =============================================================================

@app.post(
    "/api/game/new",
    response_model=ActionResponse,
    tags=["Game Management"],
    summary="Start a new game",
    description="""
Start a new game session with the specified player name.

This resets all game state and generates the starting room.
Returns the initial game state including map, player stats, and audio intent.
    """
)
async def new_game(request: NewGameRequest):
    """Start a new game session."""
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


@app.get(
    "/api/game/state",
    response_model=GameStateResponse,
    tags=["Game Management"],
    summary="Get current game state",
    description="Retrieve the complete current game state including player, room, inventory, and stats."
)
async def get_game_state():
    """Get the current game state."""
    try:
        engine = get_game_engine()
        state = engine.get_game_state()
        return GameStateResponse(**state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/game/save",
    response_model=SaveLoadResponse,
    tags=["Game Management"],
    summary="Save game",
    description="""Save the current game state to database.

**Authentication:** Optional. If authenticated, saves are linked to your user account.
Anonymous saves use 'anonymous' as player_id.

Multiple saves per user are supported."""
)
async def save_game(
    save_name: str = Query(default="quicksave", description="Name for the save slot"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Save the current game state to database."""
    try:
        engine = get_game_engine()

        # Use user ID if authenticated, otherwise anonymous
        player_id = f"user_{current_user.id}" if current_user else "anonymous"

        save_id = engine.save_to_database(player_id, save_name)

        # Update user stats if authenticated
        if current_user:
            auth_service = get_auth_service()
            auth_service.increment_games_played(current_user.id)

        return SaveLoadResponse(
            success=True,
            message=f"Game saved successfully (ID: {save_id})"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/game/load",
    response_model=SaveLoadResponse,
    tags=["Game Management"],
    summary="Load game",
    description="""Load a previously saved game state from database.

**Authentication:** Optional. If authenticated, loads from your user saves.
If save_id is not specified, loads the most recent save."""
)
async def load_game(
    save_id: Optional[int] = Query(default=None, description="Specific save ID to load"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Load saved game state from database."""
    try:
        engine = get_game_engine()

        # Use user ID if authenticated, otherwise anonymous
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/game/saves",
    tags=["Game Management"],
    summary="List saves",
    description="""List all saved games for the current user.

**Authentication:** Optional. If authenticated, lists your saves.
Anonymous users see anonymous saves."""
)
async def list_saves(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """List all saves for the current user."""
    try:
        engine = get_game_engine()

        # Use user ID if authenticated, otherwise anonymous
        player_id = f"user_{current_user.id}" if current_user else "anonymous"

        saves = engine.list_saves(player_id)
        return {
            "success": True,
            "saves": saves,
            "count": len(saves),
            "user": current_user.username if current_user else "anonymous"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete(
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
        engine = get_game_engine()

        # Verify ownership by checking if save belongs to user
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


# =============================================================================
# Movement Endpoints
# =============================================================================

@app.post(
    "/api/game/move",
    response_model=ActionResponse,
    tags=["Movement"],
    summary="Move player",
    description="""
Move the player in a cardinal direction (north, south, east, west) or vertically (up, down).

Returns success/failure, narrative description, updated map, and audio intent.
May trigger combat if entering a room with enemies.
    """
)
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
@app.post("/api/game/move/north", response_model=ActionResponse, tags=["Movement"], summary="Move north")
async def move_north():
    """Move the player north."""
    return await move(MoveRequest(direction="north"))


@app.post("/api/game/move/south", response_model=ActionResponse, tags=["Movement"], summary="Move south")
async def move_south():
    """Move the player south."""
    return await move(MoveRequest(direction="south"))


@app.post("/api/game/move/east", response_model=ActionResponse, tags=["Movement"], summary="Move east")
async def move_east():
    """Move the player east."""
    return await move(MoveRequest(direction="east"))


@app.post("/api/game/move/west", response_model=ActionResponse, tags=["Movement"], summary="Move west")
async def move_west():
    """Move the player west."""
    return await move(MoveRequest(direction="west"))


# =============================================================================
# Combat Endpoints
# =============================================================================

@app.post(
    "/api/game/combat/attack",
    response_model=ActionResponse,
    tags=["Combat"],
    summary="Attack enemy",
    description="""
Attack the current enemy in combat. Only works when in an active combat encounter.

Returns combat results including damage dealt, enemy response, and victory/defeat status.
Includes audio intents for attack sounds (THWACK!, KRAKOOM! for criticals).
    """
)
async def attack():
    """Attack the current enemy in combat."""
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


@app.post(
    "/api/game/combat/flee",
    response_model=ActionResponse,
    tags=["Combat"],
    summary="Flee from combat",
    description="""
Attempt to flee from the current combat encounter.

Success is based on player speed vs enemy speed. Failed flee attempts may result in
taking damage. Returns to exploration mode on success.
    """
)
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


# =============================================================================
# Inventory Endpoints
# =============================================================================

@app.post(
    "/api/game/take",
    response_model=ActionResponse,
    tags=["Inventory"],
    summary="Take item",
    description="Pick up an item from the current room and add it to inventory."
)
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


@app.post(
    "/api/game/use",
    response_model=ActionResponse,
    tags=["Inventory"],
    summary="Use item",
    description="""Use an item from the player's inventory.

Different item types produce different effects:
- **Potions/Elixirs**: Restore HP or provide buffs
- **Scrolls**: Cast magical effects
- **Equipment**: Equip weapons or armor

Audio feedback is generated based on the item type used."""
)
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


@app.get(
    "/api/game/inventory",
    response_model=InventoryResponse,
    tags=["Inventory"],
    summary="Get inventory",
    description="Retrieve the player's current inventory items and gold count."
)
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
@app.post(
    "/api/game/talk",
    response_model=ActionResponse,
    tags=["Interaction"],
    summary="Talk to NPC",
    description="""Initiate conversation with an NPC in the current room.

The LLM generates contextual dialogue responses based on:
- NPC personality and role
- Current game state
- Previous interactions
- Player's message content

Audio feedback reflects the NPC's mood (friendly, hostile, nervous, etc.)."""
)
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


@app.post(
    "/api/game/rest",
    response_model=ActionResponse,
    tags=["Interaction"],
    summary="Rest and recover",
    description="""Rest to recover HP and mana.

**Requirements:**
- Must be in a safe room (no enemies present)
- Cannot rest during combat

Generates peaceful ambient audio during rest."""
)
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


# =============================================================================
# Prefetch Endpoint (for performance optimization)
# =============================================================================

@app.post(
    "/api/game/prefetch",
    tags=["Game Management"],
    summary="Prefetch adjacent rooms",
    description="""Pre-generate rooms for all available exits.

This improves perceived performance by generating rooms in the background
while the player is viewing the current room."""
)
async def prefetch():
    """Prefetch adjacent rooms for faster navigation."""
    try:
        engine = get_game_engine()
        results = await engine.prefetch_adjacent_rooms()
        return {"success": True, "prefetched": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Generic action endpoint for flexibility
@app.post(
    "/api/game/action",
    response_model=ActionResponse,
    tags=["Game Management"],
    summary="Generic action",
    description="""Perform any game action through a unified endpoint.

**Supported actions:**
- `move` - Move in a direction (requires target: north/south/east/west)
- `attack` - Attack the current enemy
- `flee` - Attempt to flee from combat
- `take` - Pick up an item (requires target: item_id)
- `use` - Use an inventory item (requires target: item_id)
- `talk` - Talk to an NPC (optional target: message)
- `rest` - Rest to recover HP

This endpoint provides flexibility for custom UI implementations."""
)
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


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    """
    WebSocket endpoint for real-time game updates.

    Connect with a unique player_id to receive live game state updates.
    The connection will receive JSON messages with the following types:
    - game_update: State changes from game actions
    - error: Error notifications
    - ping: Connection health checks (respond with pong)

    Send JSON messages to perform actions:
    - {"action": "move", "direction": "north"}
    - {"action": "attack"}
    - {"action": "flee"}
    - {"action": "take", "item_id": "sword"}
    - {"action": "use", "item_id": "potion"}
    - {"action": "talk", "message": "Hello"}
    - {"action": "rest"}
    - {"type": "pong"} - Response to ping
    """
    ws_manager = get_websocket_manager()

    # Accept connection
    if not await ws_manager.connect(websocket, player_id):
        return

    engine = get_game_engine()
    audio_engine = get_audio_engine()

    try:
        # Send initial state
        await ws_manager.send_to_player(player_id, {
            "type": "connected",
            "message": f"Connected as {player_id}",
            "state": engine.get_game_state() if engine._player_state else None
        })

        while True:
            # Wait for messages from client
            data = await websocket.receive_json()

            # Handle pong responses
            if data.get("type") == "pong":
                ws_manager.update_last_ping(player_id)
                continue

            action = data.get("action")
            if not action:
                await ws_manager.send_error(player_id, "Missing 'action' field")
                continue

            result = None
            audio_data = None

            try:
                # Process game actions
                if action == "move":
                    direction = data.get("direction")
                    if not direction:
                        await ws_manager.send_error(player_id, "Missing 'direction'")
                        continue
                    result = await engine.move(direction)

                    # Generate movement audio
                    terrain = result.terrain_type if hasattr(result, 'terrain_type') else "stone"
                    audio_batch = audio_engine.generate_movement_audio(terrain)
                    audio_data = audio_batch.model_dump()

                elif action == "attack":
                    result = await engine.attack()
                    if result.success:
                        damage = result.combat_data.get("player_damage", 0) if result.combat_data else 0
                        audio_batch = audio_engine.generate_combat_audio("player_hit", damage)
                        audio_data = audio_batch.model_dump()

                elif action == "flee":
                    result = await engine.flee()
                    if result.success:
                        audio_batch = audio_engine.generate_movement_audio("run")
                        audio_data = audio_batch.model_dump()

                elif action == "take":
                    item_id = data.get("item_id")
                    if not item_id:
                        await ws_manager.send_error(player_id, "Missing 'item_id'")
                        continue
                    result = await engine.take_item(item_id)
                    if result.success:
                        item_type = "gold" if "gold" in item_id.lower() else "item"
                        audio_intent = audio_engine.generate_pickup_audio(item_type)
                        audio_data = {"primary": audio_intent.model_dump()}

                elif action == "use":
                    item_id = data.get("item_id")
                    if not item_id:
                        await ws_manager.send_error(player_id, "Missing 'item_id'")
                        continue
                    result = await engine.use_item(item_id)
                    if result.success:
                        if "potion" in item_id.lower():
                            audio_intent = audio_engine.generate_potion_audio()
                            audio_data = {"primary": audio_intent.model_dump()}

                elif action == "talk":
                    message = data.get("message", "")
                    result = await engine.talk(message)
                    if result.success and result.dialogue_data:
                        mood = result.dialogue_data.get("mood", "friendly")
                        audio_intent = audio_engine.generate_npc_reaction_audio(mood)
                        audio_data = {"primary": audio_intent.model_dump()}

                elif action == "rest":
                    result = engine.rest()

                elif action == "new_game":
                    player_name = data.get("player_name", "Adventurer")
                    reset_game_engine()
                    engine = get_game_engine()
                    result = await engine.start_new_game(player_name)

                else:
                    await ws_manager.send_error(player_id, f"Unknown action: {action}")
                    continue

                # Broadcast state update
                if result:
                    await ws_manager.broadcast_game_state(
                        player_id=player_id,
                        event_type=action,
                        state=engine.get_game_state(),
                        narrative=result.narrative,
                        audio=audio_data,
                        combat=result.combat_data,
                        dialogue=result.dialogue_data
                    )

            except Exception as e:
                await ws_manager.send_error(player_id, str(e))

    except WebSocketDisconnect:
        await ws_manager.disconnect(player_id)
    except Exception:
        await ws_manager.disconnect(player_id)


@app.get(
    "/api/ws/info",
    tags=["WebSocket"],
    summary="WebSocket connection info",
    description="Get information about how to connect to the WebSocket endpoint."
)
async def websocket_info():
    """Get WebSocket connection information."""
    ws_manager = get_websocket_manager()
    return {
        "endpoint": "/ws/{player_id}",
        "description": "Connect with a unique player_id for real-time updates",
        "active_connections": ws_manager.connection_count,
        "actions": [
            {"action": "move", "params": {"direction": "north|south|east|west"}},
            {"action": "attack", "params": {}},
            {"action": "flee", "params": {}},
            {"action": "take", "params": {"item_id": "string"}},
            {"action": "use", "params": {"item_id": "string"}},
            {"action": "talk", "params": {"message": "string (optional)"}},
            {"action": "rest", "params": {}},
            {"action": "new_game", "params": {"player_name": "string (optional)"}},
        ],
        "message_types": {
            "connected": "Initial connection confirmation with current state",
            "game_update": "State update after an action",
            "error": "Error notification",
            "ping": "Connection health check (respond with {type: 'pong'})",
        }
    }


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
