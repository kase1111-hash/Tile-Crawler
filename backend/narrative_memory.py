"""
Narrative Memory System for Tile-Crawler

Maintains a rolling log of story events to provide context to the LLM
for consistent narrative continuity and tone across the adventure.
"""

import json
import os
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NarrativeEvent(BaseModel):
    """A single narrative event in the story log."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    event_type: str  # movement, combat, dialogue, discovery, item, death
    description: str
    location: tuple[int, int, int] = (0, 0, 0)
    actors: list[str] = Field(default_factory=list)  # NPCs/enemies involved
    items: list[str] = Field(default_factory=list)  # Items involved
    importance: int = 1  # 1-5 scale, higher = more important to remember


class NarrativeMemory:
    """
    Manages the narrative memory system for story continuity.

    Keeps a rolling log of recent events that is passed to the LLM
    for context-aware content generation.
    """

    def __init__(self, save_path: str = "narrative_memory.json", max_events: int = 10):
        self.save_path = save_path
        self.max_events = max_events
        self.events: list[NarrativeEvent] = []
        self.story_summary: str = ""
        self.current_tone: str = "mysterious"
        self.active_threads: list[str] = []  # Ongoing story threads
        self.discovered_lore: list[str] = []
        self._load()

    def _load(self) -> None:
        """Load narrative memory from disk."""
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r') as f:
                    data = json.load(f)
                    self.events = [
                        NarrativeEvent(**e) for e in data.get("events", [])
                    ]
                    self.story_summary = data.get("story_summary", "")
                    self.current_tone = data.get("current_tone", "mysterious")
                    self.active_threads = data.get("active_threads", [])
                    self.discovered_lore = data.get("discovered_lore", [])
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load narrative memory: {e}")
                self._init_default()
        else:
            self._init_default()

    def _init_default(self) -> None:
        """Initialize default narrative memory."""
        self.events = []
        self.story_summary = "A brave adventurer descends into the depths of an ancient dungeon."
        self.current_tone = "mysterious"
        self.active_threads = []
        self.discovered_lore = []

    def save(self) -> None:
        """Save narrative memory to disk."""
        data = {
            "events": [e.model_dump() for e in self.events],
            "story_summary": self.story_summary,
            "current_tone": self.current_tone,
            "active_threads": self.active_threads,
            "discovered_lore": self.discovered_lore
        }
        with open(self.save_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_event(
        self,
        event_type: str,
        description: str,
        location: tuple[int, int, int] = (0, 0, 0),
        actors: Optional[list[str]] = None,
        items: Optional[list[str]] = None,
        importance: int = 1
    ) -> None:
        """Add a new narrative event to the log."""
        event = NarrativeEvent(
            event_type=event_type,
            description=description,
            location=location,
            actors=actors or [],
            items=items or [],
            importance=importance
        )
        self.events.append(event)
        self._trim_events()

    def _trim_events(self) -> None:
        """Trim events to max size, preserving important events longer."""
        if len(self.events) > self.max_events:
            # Sort by importance (descending) then by timestamp (ascending for older)
            # Keep most important and most recent
            sorted_events = sorted(
                self.events,
                key=lambda e: (e.importance, e.timestamp),
                reverse=True
            )
            self.events = sorted_events[:self.max_events]
            # Re-sort by timestamp for chronological context
            self.events.sort(key=lambda e: e.timestamp)

    def add_movement_event(
        self,
        direction: str,
        from_loc: tuple[int, int, int],
        to_loc: tuple[int, int, int],
        room_description: str
    ) -> None:
        """Record a movement event."""
        self.add_event(
            event_type="movement",
            description=f"Traveled {direction}. {room_description}",
            location=to_loc,
            importance=1
        )

    def add_combat_event(
        self,
        enemy_name: str,
        outcome: str,
        location: tuple[int, int, int],
        details: str = ""
    ) -> None:
        """Record a combat event."""
        description = f"Battled {enemy_name}. {outcome}"
        if details:
            description += f" {details}"
        self.add_event(
            event_type="combat",
            description=description,
            location=location,
            actors=[enemy_name],
            importance=3 if "boss" in enemy_name.lower() else 2
        )

    def add_dialogue_event(
        self,
        npc_name: str,
        summary: str,
        location: tuple[int, int, int]
    ) -> None:
        """Record a dialogue event."""
        self.add_event(
            event_type="dialogue",
            description=f"Spoke with {npc_name}. {summary}",
            location=location,
            actors=[npc_name],
            importance=2
        )

    def add_discovery_event(
        self,
        what: str,
        location: tuple[int, int, int],
        is_lore: bool = False
    ) -> None:
        """Record a discovery event."""
        self.add_event(
            event_type="discovery",
            description=f"Discovered {what}",
            location=location,
            importance=3 if is_lore else 2
        )
        if is_lore and what not in self.discovered_lore:
            self.discovered_lore.append(what)

    def add_item_event(
        self,
        action: str,  # "picked up", "used", "dropped"
        item_name: str,
        location: tuple[int, int, int],
        effect: str = ""
    ) -> None:
        """Record an item-related event."""
        description = f"{action.capitalize()} {item_name}"
        if effect:
            description += f". {effect}"
        self.add_event(
            event_type="item",
            description=description,
            location=location,
            items=[item_name],
            importance=1
        )

    def add_death_event(
        self,
        cause: str,
        location: tuple[int, int, int]
    ) -> None:
        """Record a player death event."""
        self.add_event(
            event_type="death",
            description=f"Fell in battle. {cause}",
            location=location,
            importance=5
        )

    def add_story_thread(self, thread: str) -> None:
        """Add an active story thread to track."""
        if thread not in self.active_threads:
            self.active_threads.append(thread)

    def resolve_story_thread(self, thread: str) -> None:
        """Mark a story thread as resolved."""
        if thread in self.active_threads:
            self.active_threads.remove(thread)

    def set_tone(self, tone: str) -> None:
        """Set the current narrative tone."""
        self.current_tone = tone

    def update_summary(self, summary: str) -> None:
        """Update the overall story summary."""
        self.story_summary = summary

    def get_context_for_llm(self) -> dict:
        """Get narrative context formatted for LLM prompts."""
        recent_events = [
            f"- {e.description}" for e in self.events[-5:]
        ]
        return {
            "story_summary": self.story_summary,
            "recent_events": recent_events,
            "current_tone": self.current_tone,
            "active_threads": self.active_threads,
            "discovered_lore": self.discovered_lore[-5:] if self.discovered_lore else []
        }

    def get_recent_events_text(self, count: int = 5) -> str:
        """Get recent events as formatted text."""
        events = self.events[-count:]
        return "\n".join([f"- {e.description}" for e in events])

    def reset(self) -> None:
        """Reset narrative memory for a new game."""
        self._init_default()
        if os.path.exists(self.save_path):
            os.remove(self.save_path)


# Global instance
_narrative_memory: Optional[NarrativeMemory] = None


def get_narrative_memory() -> NarrativeMemory:
    """Get the global narrative memory instance."""
    global _narrative_memory
    if _narrative_memory is None:
        _narrative_memory = NarrativeMemory()
    return _narrative_memory


def reset_narrative_memory() -> NarrativeMemory:
    """Reset and return fresh narrative memory."""
    global _narrative_memory
    if _narrative_memory:
        _narrative_memory.reset()
    _narrative_memory = NarrativeMemory()
    return _narrative_memory
