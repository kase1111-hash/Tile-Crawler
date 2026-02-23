"""Tests for session_manager.py — per-user game session isolation."""

import asyncio
import os
import pytest
from datetime import datetime, timedelta

from session_manager import (
    GameSession,
    SessionManager,
    get_session_manager,
    reset_session_manager,
    get_session_id_for_user,
    _session_data_dir,
)


class TestSessionDataDir:
    """Tests for session data directory helper."""

    def test_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path / "sessions"))
        path = _session_data_dir("player_1")
        assert os.path.isdir(path)
        assert path.endswith("player_1")

    def test_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path / "sessions"))
        path1 = _session_data_dir("player_1")
        path2 = _session_data_dir("player_1")
        assert path1 == path2


class TestGameSession:
    """Tests for GameSession dataclass."""

    def test_creates_isolated_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        session = GameSession(session_id="test_session")

        assert session.session_id == "test_session"
        assert session.world is not None
        assert session.narrative is not None
        assert session.inventory is not None
        assert session.player is not None

    def test_touch_updates_last_accessed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        session = GameSession(session_id="test_session")
        old_time = session.last_accessed

        session.touch()

        assert session.last_accessed >= old_time

    def test_is_expired_false_when_fresh(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        session = GameSession(session_id="test_session")

        assert session.is_expired(timeout_minutes=60) is False

    def test_is_expired_true_after_timeout(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        session = GameSession(session_id="test_session")
        # Manually backdate the last accessed time
        session.last_accessed = datetime.now() - timedelta(minutes=120)

        assert session.is_expired(timeout_minutes=60) is True


class TestSessionManager:
    """Tests for SessionManager class."""

    @pytest.fixture
    def manager(self):
        return SessionManager()

    @pytest.mark.asyncio
    async def test_get_session_creates_new(self, manager, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        session = await manager.get_session("player_1")

        assert session.session_id == "player_1"
        assert await manager.get_session_count() == 1

    @pytest.mark.asyncio
    async def test_get_session_returns_same_session(self, manager, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        session1 = await manager.get_session("player_1")
        session2 = await manager.get_session("player_1")

        assert session1 is session2

    @pytest.mark.asyncio
    async def test_get_session_different_ids_are_isolated(self, manager, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        session1 = await manager.get_session("player_1")
        session2 = await manager.get_session("player_2")

        assert session1 is not session2
        assert await manager.get_session_count() == 2

    @pytest.mark.asyncio
    async def test_create_new_session_replaces_old(self, manager, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        old_session = await manager.get_session("player_1")
        new_session = await manager.create_new_session("player_1")

        assert new_session is not old_session
        assert await manager.get_session_count() == 1

    @pytest.mark.asyncio
    async def test_delete_session_existing(self, manager, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        await manager.get_session("player_1")

        result = await manager.delete_session("player_1")

        assert result is True
        assert await manager.session_exists("player_1") is False

    @pytest.mark.asyncio
    async def test_delete_session_nonexistent(self, manager):
        result = await manager.delete_session("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_session_exists(self, manager, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        assert await manager.session_exists("player_1") is False
        await manager.get_session("player_1")
        assert await manager.session_exists("player_1") is True

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, manager, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))

        # Create two sessions
        session1 = await manager.get_session("player_1")
        await manager.get_session("player_2")

        # Expire player_1
        session1.last_accessed = datetime.now() - timedelta(minutes=120)

        cleaned = await manager.cleanup_expired_sessions()

        assert cleaned == 1
        assert await manager.session_exists("player_1") is False
        assert await manager.session_exists("player_2") is True

    @pytest.mark.asyncio
    async def test_cleanup_no_expired(self, manager, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DATA_DIR", str(tmp_path))
        await manager.get_session("player_1")

        cleaned = await manager.cleanup_expired_sessions()

        assert cleaned == 0

    def test_stop_cleanup_loop_noop_when_no_task(self, manager):
        """stop_cleanup_loop should not raise even if no task was started."""
        manager.stop_cleanup_loop()  # should not raise


class TestSessionIdForUser:
    """Tests for get_session_id_for_user helper."""

    def test_authenticated_user(self):
        assert get_session_id_for_user(42) == "user_42"

    def test_anonymous_user_default(self):
        assert get_session_id_for_user(None) == "anonymous"

    def test_anonymous_user_custom_id(self):
        assert get_session_id_for_user(None, anonymous_id="guest_abc") == "guest_abc"


class TestSingleton:
    """Tests for singleton management."""

    def test_get_session_manager_returns_same_instance(self):
        reset_session_manager()
        mgr1 = get_session_manager()
        mgr2 = get_session_manager()
        assert mgr1 is mgr2

    def test_reset_session_manager_creates_new(self):
        mgr1 = get_session_manager()
        reset_session_manager()
        mgr2 = get_session_manager()
        assert mgr1 is not mgr2

    def teardown_method(self):
        reset_session_manager()
