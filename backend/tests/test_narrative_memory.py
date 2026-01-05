"""
Tests for narrative_memory.py - Story continuity system.
"""

import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from narrative_memory import NarrativeMemory, NarrativeEvent


class TestNarrativeEvent:
    """Tests for NarrativeEvent model."""

    def test_create_event(self):
        """Test creating a narrative event."""
        event = NarrativeEvent(
            event_type="movement",
            description="Moved north into a dark corridor"
        )
        assert event.event_type == "movement"
        assert event.description == "Moved north into a dark corridor"
        assert event.importance == 1
        assert event.timestamp is not None


class TestNarrativeMemory:
    """Tests for NarrativeMemory manager."""

    def test_init_default(self, temp_dir):
        """Test initializing narrative memory."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))
        assert nm.events == []
        assert nm.current_tone == "mysterious"
        assert nm.story_summary != ""

    def test_add_event(self, temp_dir):
        """Test adding an event."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_event(
            event_type="discovery",
            description="Found an ancient artifact",
            importance=3
        )

        assert len(nm.events) == 1
        assert nm.events[0].description == "Found an ancient artifact"

    def test_add_movement_event(self, temp_dir):
        """Test adding movement event."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_movement_event(
            direction="north",
            from_loc=(0, 0, 0),
            to_loc=(0, -1, 0),
            room_description="A dark corridor stretches ahead"
        )

        assert len(nm.events) == 1
        assert "north" in nm.events[0].description.lower()

    def test_add_combat_event(self, temp_dir):
        """Test adding combat event."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_combat_event(
            enemy_name="Goblin",
            outcome="Victory",
            location=(1, 2, 0),
            details="Dealt 15 damage"
        )

        assert len(nm.events) == 1
        assert "goblin" in nm.events[0].description.lower()
        assert nm.events[0].importance >= 2

    def test_add_dialogue_event(self, temp_dir):
        """Test adding dialogue event."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_dialogue_event(
            npc_name="Old Hermit",
            summary="Spoke of ancient dangers",
            location=(0, 0, 0)
        )

        assert len(nm.events) == 1
        assert "hermit" in nm.events[0].description.lower()

    def test_add_discovery_event(self, temp_dir):
        """Test adding discovery event."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_discovery_event(
            what="the lost tomb of the king",
            location=(5, 5, 2),
            is_lore=True
        )

        assert len(nm.events) == 1
        # discovered_lore is a set/list, check if any entry contains the substring
        assert any("lost tomb" in lore.lower() for lore in nm.discovered_lore)

    def test_add_item_event(self, temp_dir):
        """Test adding item event."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_item_event(
            action="picked up",
            item_name="Ancient Key",
            location=(0, 0, 0),
            effect="It glows faintly"
        )

        assert len(nm.events) == 1
        assert "ancient key" in nm.events[0].description.lower()

    def test_add_death_event(self, temp_dir):
        """Test adding death event."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_death_event(
            cause="Overwhelmed by goblins",
            location=(3, 3, 1)
        )

        assert len(nm.events) == 1
        assert nm.events[0].importance == 5  # Death is important

    def test_trim_events(self, temp_dir):
        """Test event trimming to max size."""
        nm = NarrativeMemory(
            save_path=os.path.join(temp_dir, "narrative.json"),
            max_events=5
        )

        # Add more events than max
        for i in range(10):
            nm.add_event(
                event_type="movement",
                description=f"Event {i}",
                importance=1
            )

        assert len(nm.events) <= 5

    def test_trim_preserves_important(self, temp_dir):
        """Test that trimming preserves important events."""
        nm = NarrativeMemory(
            save_path=os.path.join(temp_dir, "narrative.json"),
            max_events=3
        )

        # Add important event first
        nm.add_event("discovery", "Important discovery", importance=5)

        # Add many low importance events
        for i in range(5):
            nm.add_event("movement", f"Minor event {i}", importance=1)

        # Important event should still be there
        descriptions = [e.description for e in nm.events]
        assert "Important discovery" in descriptions

    def test_story_threads(self, temp_dir):
        """Test managing story threads."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_story_thread("Find the lost artifact")
        nm.add_story_thread("Defeat the dragon")

        assert len(nm.active_threads) == 2

        nm.resolve_story_thread("Find the lost artifact")

        assert len(nm.active_threads) == 1
        assert "Defeat the dragon" in nm.active_threads

    def test_set_tone(self, temp_dir):
        """Test setting narrative tone."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.set_tone("dark and foreboding")

        assert nm.current_tone == "dark and foreboding"

    def test_get_context_for_llm(self, temp_dir):
        """Test getting context for LLM."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_event("movement", "Entered the dungeon")
        nm.add_discovery_event("ancient runes", (0, 0, 0), is_lore=True)

        context = nm.get_context_for_llm()

        assert "story_summary" in context
        assert "recent_events" in context
        assert "current_tone" in context
        assert "discovered_lore" in context

    def test_get_recent_events_text(self, temp_dir):
        """Test getting recent events as text."""
        nm = NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))

        nm.add_event("movement", "Event 1")
        nm.add_event("movement", "Event 2")

        text = nm.get_recent_events_text(2)

        assert "Event 1" in text
        assert "Event 2" in text

    def test_save_and_load(self, temp_dir):
        """Test saving and loading narrative memory."""
        save_path = os.path.join(temp_dir, "narrative.json")
        nm = NarrativeMemory(save_path=save_path)

        nm.add_event("discovery", "Found treasure")
        nm.add_story_thread("Quest for gold")
        nm.set_tone("adventurous")
        nm.save()

        # Load in new instance
        nm2 = NarrativeMemory(save_path=save_path)

        assert len(nm2.events) == 1
        assert nm2.current_tone == "adventurous"
        assert "Quest for gold" in nm2.active_threads
