"""Tests for WebSocket connection manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from websocket_manager import (
    WebSocketManager,
    ConnectionInfo,
    get_websocket_manager,
    reset_websocket_manager,
)


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_create_connection_info(self):
        """Test creating connection info."""
        mock_ws = MagicMock()
        info = ConnectionInfo(websocket=mock_ws, player_id="test_player")

        assert info.websocket == mock_ws
        assert info.player_id == "test_player"
        assert isinstance(info.connected_at, datetime)
        assert isinstance(info.last_ping, datetime)


class TestWebSocketManager:
    """Tests for WebSocketManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh WebSocket manager for each test."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_success(self, manager, mock_websocket):
        """Test successful connection."""
        result = await manager.connect(mock_websocket, "player1")

        assert result is True
        assert manager.is_connected("player1")
        assert manager.connection_count == 1
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_replaces_existing(self, manager, mock_websocket):
        """Test that new connection replaces existing one for same player."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.close = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.close = AsyncMock()

        await manager.connect(ws1, "player1")
        await manager.connect(ws2, "player1")

        assert manager.connection_count == 1
        ws1.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a player."""
        await manager.connect(mock_websocket, "player1")
        await manager.disconnect("player1")

        assert not manager.is_connected("player1")
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self, manager):
        """Test disconnecting a player that doesn't exist."""
        # Should not raise
        await manager.disconnect("nonexistent")

    @pytest.mark.asyncio
    async def test_send_to_player(self, manager, mock_websocket):
        """Test sending message to specific player."""
        await manager.connect(mock_websocket, "player1")

        result = await manager.send_to_player("player1", {"test": "data"})

        assert result is True
        mock_websocket.send_json.assert_called_once_with({"test": "data"})

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_player(self, manager):
        """Test sending to player that doesn't exist."""
        result = await manager.send_to_player("nonexistent", {"test": "data"})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_removes_dead_connection(self, manager, mock_websocket):
        """Test that dead connections are removed on send failure."""
        mock_websocket.send_json.side_effect = Exception("Connection closed")
        await manager.connect(mock_websocket, "player1")

        result = await manager.send_to_player("player1", {"test": "data"})

        assert result is False
        assert not manager.is_connected("player1")

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all players."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, "player1")
        await manager.connect(ws2, "player2")

        count = await manager.broadcast({"message": "hello"})

        assert count == 2
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self, manager):
        """Test broadcasting with exclusions."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, "player1")
        await manager.connect(ws2, "player2")

        count = await manager.broadcast({"message": "hello"}, exclude={"player1"})

        assert count == 1
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_game_state(self, manager, mock_websocket):
        """Test broadcasting game state update."""
        await manager.connect(mock_websocket, "player1")

        result = await manager.broadcast_game_state(
            player_id="player1",
            event_type="move",
            state={"player": {"hp": 100}},
            narrative="You moved north."
        )

        assert result is True
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "game_update"
        assert call_args["event"] == "move"
        assert call_args["data"]["state"] == {"player": {"hp": 100}}
        assert call_args["data"]["narrative"] == "You moved north."

    @pytest.mark.asyncio
    async def test_send_error(self, manager, mock_websocket):
        """Test sending error message."""
        await manager.connect(mock_websocket, "player1")

        result = await manager.send_error("player1", "Something went wrong")

        assert result is True
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["message"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_send_ping(self, manager, mock_websocket):
        """Test sending ping."""
        await manager.connect(mock_websocket, "player1")

        result = await manager.send_ping("player1")

        assert result is True
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "ping"

    def test_update_last_ping(self, manager):
        """Test updating last ping time."""
        # Create a connection manually for this test
        mock_ws = MagicMock()
        info = ConnectionInfo(websocket=mock_ws, player_id="player1")
        manager._connections["player1"] = info

        old_ping = info.last_ping
        manager.update_last_ping("player1")

        assert manager._connections["player1"].last_ping >= old_ping

    def test_get_connected_players(self, manager):
        """Test getting set of connected players."""
        # Create connections manually
        for player_id in ["player1", "player2", "player3"]:
            mock_ws = MagicMock()
            manager._connections[player_id] = ConnectionInfo(
                websocket=mock_ws, player_id=player_id
            )

        players = manager.get_connected_players()

        assert players == {"player1", "player2", "player3"}


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_websocket_manager_returns_same_instance(self):
        """Test that get_websocket_manager returns singleton."""
        reset_websocket_manager()
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()

        assert manager1 is manager2

    def test_reset_websocket_manager(self):
        """Test that reset creates new instance."""
        manager1 = get_websocket_manager()
        reset_websocket_manager()
        manager2 = get_websocket_manager()

        assert manager1 is not manager2
