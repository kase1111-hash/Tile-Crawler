"""
Game Repository - Database abstraction layer

Provides a unified interface for game state persistence with support for
SQLite (default) and PostgreSQL backends.
"""

import os
import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from .models import GameSave, PlayerData, WorldData, InventoryData, NarrativeData, CombatData


class BaseRepository(ABC):
    """Abstract base class for game repositories."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the database schema."""
        pass

    @abstractmethod
    def save_game(self, save: GameSave) -> int:
        """Save game state. Returns save ID."""
        pass

    @abstractmethod
    def load_game(self, save_id: Optional[int] = None, player_id: str = "default") -> Optional[GameSave]:
        """Load game state by ID or most recent for player."""
        pass

    @abstractmethod
    def delete_game(self, save_id: int) -> bool:
        """Delete a saved game."""
        pass

    @abstractmethod
    def list_saves(self, player_id: str = "default") -> List[dict]:
        """List all saves for a player."""
        pass

    @abstractmethod
    def get_save_count(self, player_id: str = "default") -> int:
        """Get number of saves for a player."""
        pass


class SQLiteRepository(BaseRepository):
    """SQLite implementation of game repository."""

    def __init__(self, db_path: str = "game_data.db"):
        self.db_path = db_path
        self._initialized = False

    @contextmanager
    def _get_connection(self):
        """Get a database connection with context management."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create database tables if they don't exist."""
        if self._initialized:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Main game saves table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_saves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_name TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version TEXT DEFAULT '1.0.0',
                    playtime_seconds INTEGER DEFAULT 0,
                    player_data TEXT NOT NULL,
                    world_data TEXT NOT NULL,
                    inventory_data TEXT NOT NULL,
                    narrative_data TEXT NOT NULL,
                    combat_data TEXT
                )
            """)

            # Index for faster player lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_player_id ON game_saves(player_id)
            """)

            # Index for recent saves
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_updated_at ON game_saves(updated_at DESC)
            """)

        self._initialized = True

    def save_game(self, save: GameSave) -> int:
        """Save game state to SQLite."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            player_json = save.player.model_dump_json()
            world_json = save.world.model_dump_json()
            inventory_json = save.inventory.model_dump_json()
            narrative_json = save.narrative.model_dump_json()
            combat_json = save.combat.model_dump_json() if save.combat else None

            if save.id:
                # Update existing save
                cursor.execute("""
                    UPDATE game_saves SET
                        save_name = ?,
                        updated_at = ?,
                        version = ?,
                        playtime_seconds = ?,
                        player_data = ?,
                        world_data = ?,
                        inventory_data = ?,
                        narrative_data = ?,
                        combat_data = ?
                    WHERE id = ?
                """, (
                    save.save_name,
                    datetime.now().isoformat(),
                    save.version,
                    save.playtime_seconds,
                    player_json,
                    world_json,
                    inventory_json,
                    narrative_json,
                    combat_json,
                    save.id
                ))
                return save.id
            else:
                # Create new save
                cursor.execute("""
                    INSERT INTO game_saves (
                        save_name, player_id, created_at, updated_at,
                        version, playtime_seconds,
                        player_data, world_data, inventory_data,
                        narrative_data, combat_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    save.save_name,
                    save.player_id,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    save.version,
                    save.playtime_seconds,
                    player_json,
                    world_json,
                    inventory_json,
                    narrative_json,
                    combat_json
                ))
                return cursor.lastrowid

    def load_game(self, save_id: Optional[int] = None, player_id: str = "default") -> Optional[GameSave]:
        """Load game state from SQLite."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if save_id:
                cursor.execute("""
                    SELECT * FROM game_saves WHERE id = ?
                """, (save_id,))
            else:
                # Get most recent save for player
                cursor.execute("""
                    SELECT * FROM game_saves
                    WHERE player_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (player_id,))

            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_save(row)

    def _row_to_save(self, row: sqlite3.Row) -> GameSave:
        """Convert database row to GameSave model."""
        player_data = PlayerData.model_validate_json(row["player_data"])
        world_data = WorldData.model_validate_json(row["world_data"])
        inventory_data = InventoryData.model_validate_json(row["inventory_data"])
        narrative_data = NarrativeData.model_validate_json(row["narrative_data"])
        combat_data = None
        if row["combat_data"]:
            combat_data = CombatData.model_validate_json(row["combat_data"])

        return GameSave(
            id=row["id"],
            save_name=row["save_name"],
            player_id=row["player_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            version=row["version"],
            playtime_seconds=row["playtime_seconds"],
            player=player_data,
            world=world_data,
            inventory=inventory_data,
            narrative=narrative_data,
            combat=combat_data
        )

    def delete_game(self, save_id: int) -> bool:
        """Delete a saved game."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM game_saves WHERE id = ?", (save_id,))
            return cursor.rowcount > 0

    def list_saves(self, player_id: str = "default") -> List[dict]:
        """List all saves for a player."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, save_name, created_at, updated_at, playtime_seconds
                FROM game_saves
                WHERE player_id = ?
                ORDER BY updated_at DESC
            """, (player_id,))

            return [
                {
                    "id": row["id"],
                    "save_name": row["save_name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "playtime_seconds": row["playtime_seconds"]
                }
                for row in cursor.fetchall()
            ]

    def get_save_count(self, player_id: str = "default") -> int:
        """Get number of saves for a player."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM game_saves WHERE player_id = ?
            """, (player_id,))
            return cursor.fetchone()[0]


class PostgreSQLRepository(BaseRepository):
    """PostgreSQL implementation of game repository."""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            "postgresql://localhost/tile_crawler"
        )
        self._initialized = False
        self._pool = None

    def _get_pool(self):
        """Get or create connection pool."""
        if self._pool is None:
            try:
                import psycopg2
                from psycopg2 import pool as pg_pool
                self._pool = pg_pool.SimpleConnectionPool(
                    1, 10,
                    self.connection_string
                )
            except ImportError:
                raise ImportError(
                    "PostgreSQL support requires psycopg2. "
                    "Install with: pip install psycopg2-binary"
                )
        return self._pool

    @contextmanager
    def _get_connection(self):
        """Get a database connection from pool."""
        pool = self._get_pool()
        conn = pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            pool.putconn(conn)

    def initialize(self) -> None:
        """Create database tables if they don't exist."""
        if self._initialized:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS game_saves (
                    id SERIAL PRIMARY KEY,
                    save_name VARCHAR(255) NOT NULL,
                    player_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version VARCHAR(50) DEFAULT '1.0.0',
                    playtime_seconds INTEGER DEFAULT 0,
                    player_data JSONB NOT NULL,
                    world_data JSONB NOT NULL,
                    inventory_data JSONB NOT NULL,
                    narrative_data JSONB NOT NULL,
                    combat_data JSONB
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_game_saves_player_id
                ON game_saves(player_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_game_saves_updated_at
                ON game_saves(updated_at DESC)
            """)

        self._initialized = True

    def save_game(self, save: GameSave) -> int:
        """Save game state to PostgreSQL."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            player_json = save.player.model_dump()
            world_json = save.world.model_dump()
            inventory_json = save.inventory.model_dump()
            narrative_json = save.narrative.model_dump()
            combat_json = save.combat.model_dump() if save.combat else None

            if save.id:
                cursor.execute("""
                    UPDATE game_saves SET
                        save_name = %s,
                        updated_at = %s,
                        version = %s,
                        playtime_seconds = %s,
                        player_data = %s,
                        world_data = %s,
                        inventory_data = %s,
                        narrative_data = %s,
                        combat_data = %s
                    WHERE id = %s
                    RETURNING id
                """, (
                    save.save_name,
                    datetime.now(),
                    save.version,
                    save.playtime_seconds,
                    json.dumps(player_json),
                    json.dumps(world_json),
                    json.dumps(inventory_json),
                    json.dumps(narrative_json),
                    json.dumps(combat_json) if combat_json else None,
                    save.id
                ))
                return cursor.fetchone()[0]
            else:
                cursor.execute("""
                    INSERT INTO game_saves (
                        save_name, player_id, created_at, updated_at,
                        version, playtime_seconds,
                        player_data, world_data, inventory_data,
                        narrative_data, combat_data
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    save.save_name,
                    save.player_id,
                    datetime.now(),
                    datetime.now(),
                    save.version,
                    save.playtime_seconds,
                    json.dumps(player_json),
                    json.dumps(world_json),
                    json.dumps(inventory_json),
                    json.dumps(narrative_json),
                    json.dumps(combat_json) if combat_json else None
                ))
                return cursor.fetchone()[0]

    def load_game(self, save_id: Optional[int] = None, player_id: str = "default") -> Optional[GameSave]:
        """Load game state from PostgreSQL."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if save_id:
                cursor.execute("""
                    SELECT * FROM game_saves WHERE id = %s
                """, (save_id,))
            else:
                cursor.execute("""
                    SELECT * FROM game_saves
                    WHERE player_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (player_id,))

            row = cursor.fetchone()

            if not row:
                return None

            # Get column names
            columns = [desc[0] for desc in cursor.description]
            row_dict = dict(zip(columns, row))

            return self._row_to_save(row_dict)

    def _row_to_save(self, row: dict) -> GameSave:
        """Convert database row to GameSave model."""
        player_data = PlayerData.model_validate(row["player_data"])
        world_data = WorldData.model_validate(row["world_data"])
        inventory_data = InventoryData.model_validate(row["inventory_data"])
        narrative_data = NarrativeData.model_validate(row["narrative_data"])
        combat_data = None
        if row["combat_data"]:
            combat_data = CombatData.model_validate(row["combat_data"])

        return GameSave(
            id=row["id"],
            save_name=row["save_name"],
            player_id=row["player_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
            playtime_seconds=row["playtime_seconds"],
            player=player_data,
            world=world_data,
            inventory=inventory_data,
            narrative=narrative_data,
            combat=combat_data
        )

    def delete_game(self, save_id: int) -> bool:
        """Delete a saved game."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM game_saves WHERE id = %s", (save_id,))
            return cursor.rowcount > 0

    def list_saves(self, player_id: str = "default") -> List[dict]:
        """List all saves for a player."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, save_name, created_at, updated_at, playtime_seconds
                FROM game_saves
                WHERE player_id = %s
                ORDER BY updated_at DESC
            """, (player_id,))

            columns = ["id", "save_name", "created_at", "updated_at", "playtime_seconds"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_save_count(self, player_id: str = "default") -> int:
        """Get number of saves for a player."""
        self.initialize()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM game_saves WHERE player_id = %s
            """, (player_id,))
            return cursor.fetchone()[0]

    def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None


class GameRepository:
    """
    Unified game repository that automatically selects the appropriate backend.

    Usage:
        repo = GameRepository()  # Uses SQLite by default
        repo = GameRepository(backend="postgresql")  # Uses PostgreSQL
    """

    def __init__(
        self,
        backend: str = "sqlite",
        db_path: str = "game_data.db",
        connection_string: Optional[str] = None
    ):
        self.backend = backend.lower()

        if self.backend == "sqlite":
            self._repo = SQLiteRepository(db_path)
        elif self.backend in ("postgresql", "postgres", "pg"):
            self._repo = PostgreSQLRepository(connection_string)
        else:
            raise ValueError(f"Unknown database backend: {backend}")

        self._repo.initialize()

    def save_game(self, save: GameSave) -> int:
        """Save game state."""
        return self._repo.save_game(save)

    def load_game(self, save_id: Optional[int] = None, player_id: str = "default") -> Optional[GameSave]:
        """Load game state."""
        return self._repo.load_game(save_id, player_id)

    def delete_game(self, save_id: int) -> bool:
        """Delete a saved game."""
        return self._repo.delete_game(save_id)

    def list_saves(self, player_id: str = "default") -> List[dict]:
        """List all saves for a player."""
        return self._repo.list_saves(player_id)

    def get_save_count(self, player_id: str = "default") -> int:
        """Get number of saves for a player."""
        return self._repo.get_save_count(player_id)

    def quick_save(self, player_id: str = "default") -> GameSave:
        """Create an empty save placeholder for quick saving."""
        return GameSave(player_id=player_id, save_name="quicksave")


# Singleton management
_repository: Optional[GameRepository] = None


def get_repository(
    backend: Optional[str] = None,
    db_path: str = "game_data.db",
    connection_string: Optional[str] = None
) -> GameRepository:
    """Get the singleton repository instance."""
    global _repository

    # Determine backend from environment if not specified
    if backend is None:
        backend = os.getenv("DB_BACKEND", "sqlite")

    if _repository is None:
        _repository = GameRepository(
            backend=backend,
            db_path=db_path,
            connection_string=connection_string
        )

    return _repository


def reset_repository() -> None:
    """Reset the repository singleton (for testing)."""
    global _repository
    _repository = None
