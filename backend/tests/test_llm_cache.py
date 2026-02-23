"""Tests for llm_cache.py — LRU cache for LLM room generation responses."""

import pytest

from llm_cache import (
    LLMCache,
    CachedRoom,
    _depth_range,
    _cache_key,
    get_llm_cache,
)


def _make_room(biome="dungeon", enemies=None, npcs=None):
    """Helper to build a CachedRoom for testing."""
    return CachedRoom(
        biome=biome,
        depth_range="0-2",
        map=["▓▓▓", "▓░▓", "▓▓▓"],
        description=f"A {biome} room",
        enemies=enemies or [],
        items=[],
        npcs=npcs or [],
        features=["torch"],
    )


class TestDepthRange:
    """Tests for the depth-bucketing helper."""

    def test_shallow(self):
        for z in (0, 1, 2):
            assert _depth_range(z) == "0-2"

    def test_mid(self):
        for z in (3, 4, 5):
            assert _depth_range(z) == "3-5"

    def test_deep(self):
        assert _depth_range(6) == "6-7"
        assert _depth_range(7) == "6-7"

    def test_very_deep(self):
        assert _depth_range(8) == "8+"
        assert _depth_range(99) == "8+"


class TestCacheKey:
    """Tests for cache key construction."""

    def test_basic_key(self):
        key = _cache_key("dungeon", 0, has_enemies=False, has_npcs=False)
        assert key == "dungeon:0-2:e0:n0"

    def test_key_with_enemies(self):
        key = _cache_key("cave", 4, has_enemies=True, has_npcs=False)
        assert key == "cave:3-5:e1:n0"

    def test_key_with_npcs(self):
        key = _cache_key("temple", 7, has_enemies=False, has_npcs=True)
        assert key == "temple:6-7:e0:n1"

    def test_key_with_both(self):
        key = _cache_key("ruins", 10, has_enemies=True, has_npcs=True)
        assert key == "ruins:8+:e1:n1"


class TestLLMCache:
    """Tests for LLMCache class."""

    @pytest.fixture
    def cache(self):
        return LLMCache(max_size=5)

    def test_miss_returns_none(self, cache):
        result = cache.get("dungeon", 0, False, False)
        assert result is None

    def test_put_and_get(self, cache):
        room = _make_room("dungeon")
        cache.put("dungeon", 0, room)

        result = cache.get("dungeon", 0, False, False)
        assert result is not None
        assert result.biome == "dungeon"

    def test_size_tracks_entries(self, cache):
        assert cache.size == 0

        cache.put("dungeon", 0, _make_room("dungeon"))
        assert cache.size == 1

        cache.put("dungeon", 0, _make_room("dungeon"))
        assert cache.size == 2  # same key, second variant

    def test_max_variants_per_key(self, cache):
        """Each key holds at most 3 variants."""
        for i in range(5):
            cache.put("dungeon", 0, _make_room("dungeon"))

        # Only 3 variants stored per key
        assert cache.size == 3

    def test_different_keys_stored_separately(self, cache):
        cache.put("dungeon", 0, _make_room("dungeon"))
        cache.put("cave", 0, _make_room("cave"))

        dungeon = cache.get("dungeon", 0, False, False)
        cave = cache.get("cave", 0, False, False)

        assert dungeon.biome == "dungeon"
        assert cave.biome == "cave"

    def test_enemies_flag_changes_key(self, cache):
        room_no_enemies = _make_room("dungeon")
        room_with_enemies = _make_room("dungeon", enemies=[{"id": "goblin"}])

        cache.put("dungeon", 0, room_no_enemies)
        cache.put("dungeon", 0, room_with_enemies)

        no_enemy = cache.get("dungeon", 0, has_enemies=False, has_npcs=False)
        with_enemy = cache.get("dungeon", 0, has_enemies=True, has_npcs=False)

        assert no_enemy is not None
        assert with_enemy is not None
        assert len(no_enemy.enemies) == 0
        assert len(with_enemy.enemies) == 1

    def test_lru_eviction(self):
        """Oldest keys are evicted when max_size exceeded."""
        cache = LLMCache(max_size=2)

        cache.put("dungeon", 0, _make_room("dungeon"))
        cache.put("cave", 0, _make_room("cave"))
        cache.put("crypt", 0, _make_room("crypt"))  # should evict "dungeon"

        assert cache.get("dungeon", 0, False, False) is None
        assert cache.get("cave", 0, False, False) is not None
        assert cache.get("crypt", 0, False, False) is not None

    def test_get_refreshes_lru_order(self):
        """Accessing a key moves it to the end, preventing eviction."""
        cache = LLMCache(max_size=2)

        cache.put("dungeon", 0, _make_room("dungeon"))
        cache.put("cave", 0, _make_room("cave"))

        # Access "dungeon" to refresh it
        cache.get("dungeon", 0, False, False)

        # Now "cave" is oldest — inserting a new key evicts "cave"
        cache.put("crypt", 0, _make_room("crypt"))

        assert cache.get("dungeon", 0, False, False) is not None
        assert cache.get("cave", 0, False, False) is None

    def test_clear(self, cache):
        cache.put("dungeon", 0, _make_room("dungeon"))
        cache.put("cave", 0, _make_room("cave"))

        cache.clear()

        assert cache.size == 0
        assert cache.get("dungeon", 0, False, False) is None

    def test_depth_bucketing_in_cache(self, cache):
        """Rooms at z=1 and z=2 share the same cache bucket."""
        room = _make_room("dungeon")
        cache.put("dungeon", 1, room)

        # z=2 is in the same "0-2" bucket
        result = cache.get("dungeon", 2, False, False)
        assert result is not None


class TestCachedRoomModel:
    """Tests for CachedRoom Pydantic model."""

    def test_create_cached_room(self):
        room = CachedRoom(
            biome="dungeon",
            depth_range="0-2",
            map=["###"],
            description="test",
            enemies=[],
            items=[{"id": "key"}],
            npcs=["merchant"],
            features=["torch"],
        )
        assert room.biome == "dungeon"
        assert len(room.items) == 1
        assert len(room.npcs) == 1


class TestSingleton:
    """Tests for module-level singleton."""

    def test_get_llm_cache_returns_instance(self):
        cache = get_llm_cache()
        assert isinstance(cache, LLMCache)

    def test_get_llm_cache_is_singleton(self):
        cache1 = get_llm_cache()
        cache2 = get_llm_cache()
        assert cache1 is cache2
