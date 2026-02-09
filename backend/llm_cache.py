"""
LLM Response Cache for Tile-Crawler

Simple LRU cache for LLM-generated rooms. Cache key is (biome, depth_range,
has_enemies, has_npcs). On cache hit, returns a stored room with randomized
enemy/item placement for variety.
"""

import random
from collections import OrderedDict
from typing import Optional
from pydantic import BaseModel


class CachedRoom(BaseModel):
    """A cached room response with its generation parameters."""
    biome: str
    depth_range: str  # e.g., "0-2", "3-5"
    map: list[str]
    description: str
    enemies: list[dict]
    items: list[dict]
    npcs: list[str]
    features: list[str]


def _depth_range(z: int) -> str:
    """Bucket depth into ranges for cache key granularity."""
    if z <= 2:
        return "0-2"
    elif z <= 5:
        return "3-5"
    elif z <= 7:
        return "6-7"
    else:
        return "8+"


def _cache_key(biome: str, z: int, has_enemies: bool, has_npcs: bool) -> str:
    """Build a cache key from room parameters."""
    return f"{biome}:{_depth_range(z)}:e{int(has_enemies)}:n{int(has_npcs)}"


class LLMCache:
    """LRU cache for LLM room generation responses."""

    def __init__(self, max_size: int = 30):
        self.max_size = max_size
        self._cache: OrderedDict[str, list[CachedRoom]] = OrderedDict()

    def get(self, biome: str, z: int, has_enemies: bool, has_npcs: bool) -> Optional[CachedRoom]:
        """Look up a cached room. Returns None on miss."""
        key = _cache_key(biome, z, has_enemies, has_npcs)
        if key not in self._cache:
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)

        entries = self._cache[key]
        if not entries:
            return None

        # Return a random entry from the bucket for variety
        return random.choice(entries)

    def put(self, biome: str, z: int, room: CachedRoom) -> None:
        """Store a room in the cache."""
        has_enemies = len(room.enemies) > 0
        has_npcs = len(room.npcs) > 0
        key = _cache_key(biome, z, has_enemies, has_npcs)

        if key not in self._cache:
            self._cache[key] = []

        # Store up to 3 variants per key for variety
        bucket = self._cache[key]
        if len(bucket) < 3:
            bucket.append(room)
        else:
            # Replace oldest variant
            bucket[random.randint(0, 2)] = room

        self._cache.move_to_end(key)

        # Evict oldest keys if over capacity
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()

    @property
    def size(self) -> int:
        """Total number of cached entries across all keys."""
        return sum(len(v) for v in self._cache.values())


# Module-level singleton
_llm_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """Get the global LLM cache instance."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache
