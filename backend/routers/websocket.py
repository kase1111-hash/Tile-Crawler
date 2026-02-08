"""WebSocket endpoints (only active when WEBSOCKET_ENABLED=true)."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from game_engine import get_game_engine, reset_game_engine
from websocket_manager import get_websocket_manager

router = APIRouter()


@router.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    """
    WebSocket endpoint for real-time game updates.

    Connect with a unique player_id to receive live game state updates.
    """
    ws_manager = get_websocket_manager()

    if not await ws_manager.connect(websocket, player_id):
        return

    engine = get_game_engine()

    try:
        await ws_manager.send_to_player(player_id, {
            "type": "connected",
            "message": f"Connected as {player_id}",
            "state": engine.get_game_state() if engine._player_state else None
        })

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "pong":
                await ws_manager.update_last_ping(player_id)
                continue

            action = data.get("action")
            if not action:
                await ws_manager.send_error(player_id, "Missing 'action' field")
                continue

            result = None

            try:
                if action == "move":
                    direction = data.get("direction")
                    if not direction:
                        await ws_manager.send_error(player_id, "Missing 'direction'")
                        continue
                    result = await engine.move(direction)

                elif action == "attack":
                    result = await engine.attack()

                elif action == "flee":
                    result = await engine.flee()

                elif action == "take":
                    item_id = data.get("item_id")
                    if not item_id:
                        await ws_manager.send_error(player_id, "Missing 'item_id'")
                        continue
                    result = await engine.take_item(item_id)

                elif action == "use":
                    item_id = data.get("item_id")
                    if not item_id:
                        await ws_manager.send_error(player_id, "Missing 'item_id'")
                        continue
                    result = await engine.use_item(item_id)

                elif action == "talk":
                    message = data.get("message", "")
                    result = await engine.talk(message)

                elif action == "rest":
                    result = engine.rest()

                elif action == "new_game":
                    player_name = data.get("player_name", "Adventurer")
                    reset_game_engine()
                    engine = get_game_engine()
                    result = await engine.new_game(player_name)

                else:
                    await ws_manager.send_error(player_id, f"Unknown action: {action}")
                    continue

                if result:
                    await ws_manager.broadcast_game_state(
                        player_id=player_id,
                        event_type=action,
                        state=engine.get_game_state(),
                        narrative=result.narrative,
                        combat=result.combat_data,
                        dialogue=result.dialogue_data
                    )

            except Exception as e:
                await ws_manager.send_error(player_id, str(e))

    except WebSocketDisconnect:
        await ws_manager.disconnect(player_id)
    except Exception:
        await ws_manager.disconnect(player_id)


@router.get(
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
    }
