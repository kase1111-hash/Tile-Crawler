"""
WebSocket Connection Manager for Tile-Crawler

Manages WebSocket connections and broadcasts game state updates in real-time.
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    player_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time game updates.

    Features:
    - Connection tracking by player ID
    - Broadcast to all or specific players
    - Heartbeat/ping monitoring
    - Graceful disconnect handling
    """

    def __init__(self):
        self._connections: Dict[str, ConnectionInfo] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, player_id: str) -> bool:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept
            player_id: Unique identifier for the player

        Returns:
            True if connection was accepted successfully
        """
        try:
            await websocket.accept()
            async with self._lock:
                # Close existing connection for this player if any
                if player_id in self._connections:
                    old_conn = self._connections[player_id]
                    try:
                        await old_conn.websocket.close(code=1000, reason="New connection")
                    except Exception:
                        pass

                self._connections[player_id] = ConnectionInfo(
                    websocket=websocket,
                    player_id=player_id
                )
            return True
        except Exception:
            return False

    async def disconnect(self, player_id: str) -> None:
        """Remove a player's connection."""
        async with self._lock:
            if player_id in self._connections:
                try:
                    await self._connections[player_id].websocket.close()
                except Exception:
                    pass
                del self._connections[player_id]

    async def send_to_player(self, player_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific player.

        Args:
            player_id: The player to send to
            message: The message data to send

        Returns:
            True if message was sent successfully
        """
        async with self._lock:
            if player_id not in self._connections:
                return False

            conn = self._connections[player_id]
            try:
                await conn.websocket.send_json(message)
                return True
            except Exception:
                # Connection is dead, remove it
                del self._connections[player_id]
                return False

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[Set[str]] = None) -> int:
        """
        Broadcast a message to all connected players.

        Args:
            message: The message data to broadcast
            exclude: Set of player IDs to exclude from broadcast

        Returns:
            Number of players the message was sent to
        """
        exclude = exclude or set()
        sent_count = 0
        dead_connections = []

        async with self._lock:
            for player_id, conn in self._connections.items():
                if player_id in exclude:
                    continue

                try:
                    await conn.websocket.send_json(message)
                    sent_count += 1
                except Exception:
                    dead_connections.append(player_id)

            # Clean up dead connections
            for player_id in dead_connections:
                del self._connections[player_id]

        return sent_count

    async def broadcast_game_state(
        self,
        player_id: str,
        event_type: str,
        state: Dict[str, Any],
        narrative: Optional[str] = None,
        audio: Optional[Dict[str, Any]] = None,
        combat: Optional[Dict[str, Any]] = None,
        dialogue: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Broadcast a game state update to a specific player.

        Args:
            player_id: The player to send the update to
            event_type: Type of game event (move, attack, item, etc.)
            state: Current game state
            narrative: Optional narrative text
            audio: Optional audio intent data
            combat: Optional combat data
            dialogue: Optional dialogue data

        Returns:
            True if broadcast was successful
        """
        message = {
            "type": "game_update",
            "event": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "state": state,
                "narrative": narrative,
                "audio": audio,
                "combat": combat,
                "dialogue": dialogue
            }
        }
        return await self.send_to_player(player_id, message)

    async def send_error(self, player_id: str, error: str) -> bool:
        """Send an error message to a player."""
        return await self.send_to_player(player_id, {
            "type": "error",
            "message": error,
            "timestamp": datetime.now().isoformat()
        })

    async def send_ping(self, player_id: str) -> bool:
        """Send a ping to a player to check connection health."""
        return await self.send_to_player(player_id, {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        })

    async def update_last_ping(self, player_id: str) -> None:
        """Update the last ping time for a player (called when pong received)."""
        async with self._lock:
            if player_id in self._connections:
                self._connections[player_id].last_ping = datetime.now()

    @property
    def connection_count(self) -> int:
        """Get the number of active connections (snapshot, may be stale)."""
        # Note: This is a quick snapshot for metrics. For critical operations,
        # use async methods with proper locking.
        return len(self._connections)

    async def is_connected(self, player_id: str) -> bool:
        """Check if a player is connected."""
        async with self._lock:
            return player_id in self._connections

    async def get_connected_players(self) -> Set[str]:
        """Get set of all connected player IDs."""
        async with self._lock:
            return set(self._connections.keys())


# Singleton instance
_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get the singleton WebSocket manager instance."""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager


def reset_websocket_manager() -> None:
    """Reset the WebSocket manager (for testing)."""
    global _manager
    _manager = None
