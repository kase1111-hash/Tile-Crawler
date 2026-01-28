"""
Session Manager for Tile-Crawler

Manages per-user game sessions to support multiple concurrent users.
Each user gets their own isolated game engine instance.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass, field

from world_state import WorldState
from narrative_memory import NarrativeMemory
from inventory_state import InventoryState
from player_state import PlayerState
from llm_engine import get_llm_engine


# Session timeout in minutes (cleanup inactive sessions)
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))


@dataclass
class GameSession:
    """A single user's game session with isolated state."""
    session_id: str
    world: WorldState = field(default_factory=WorldState)
    narrative: NarrativeMemory = field(default_factory=NarrativeMemory)
    inventory: InventoryState = field(default_factory=InventoryState)
    player: PlayerState = field(default_factory=PlayerState)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = datetime.now()

    def is_expired(self, timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> bool:
        """Check if session has expired due to inactivity."""
        return datetime.now() - self.last_accessed > timedelta(minutes=timeout_minutes)


class SessionManager:
    """
    Manages game sessions for multiple users.

    Each user gets their own isolated game state, preventing
    state bleeding between concurrent users.
    """

    def __init__(self):
        self._sessions: Dict[str, GameSession] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def get_session(self, session_id: str) -> GameSession:
        """
        Get or create a game session for the given session ID.

        Args:
            session_id: Unique identifier (user_id for auth users, temp ID for anonymous)

        Returns:
            GameSession for this user
        """
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = GameSession(session_id=session_id)

            session = self._sessions[session_id]
            session.touch()
            return session

    async def create_new_session(self, session_id: str) -> GameSession:
        """
        Create a fresh session, replacing any existing one.

        Args:
            session_id: Unique identifier

        Returns:
            New GameSession
        """
        async with self._lock:
            self._sessions[session_id] = GameSession(session_id=session_id)
            return self._sessions[session_id]

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Returns:
            True if session was deleted, False if not found
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        async with self._lock:
            return session_id in self._sessions

    async def get_session_count(self) -> int:
        """Get the number of active sessions."""
        async with self._lock:
            return len(self._sessions)

    async def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        async with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)

    async def start_cleanup_loop(self, interval_minutes: int = 5) -> None:
        """Start background task to cleanup expired sessions."""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_minutes * 60)
                cleaned = await self.cleanup_expired_sessions()
                if cleaned > 0:
                    print(f"Session cleanup: removed {cleaned} expired sessions")

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    def stop_cleanup_loop(self) -> None:
        """Stop the cleanup background task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the singleton session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def reset_session_manager() -> None:
    """Reset the session manager (for testing)."""
    global _session_manager
    _session_manager = None


def get_session_id_for_user(user_id: Optional[int], anonymous_id: str = "anonymous") -> str:
    """
    Get session ID for a user.

    Args:
        user_id: User ID if authenticated, None otherwise
        anonymous_id: ID to use for unauthenticated users

    Returns:
        Session ID string
    """
    if user_id is not None:
        return f"user_{user_id}"
    return anonymous_id
