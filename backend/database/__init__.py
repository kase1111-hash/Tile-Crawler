"""
Database package for Tile-Crawler

Provides abstraction layer for game state persistence with support for:
- SQLite (default, file-based)
- PostgreSQL (scalable, production-ready)
"""

from .repository import GameRepository, get_repository, reset_repository
from .models import GameSave, PlayerData, WorldData, InventoryData, NarrativeData

__all__ = [
    "GameRepository",
    "get_repository",
    "reset_repository",
    "GameSave",
    "PlayerData",
    "WorldData",
    "InventoryData",
    "NarrativeData",
]
