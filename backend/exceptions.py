"""Game-specific exceptions for Tile-Crawler."""


class TileCrawlerError(Exception):
    """Base exception for all game errors."""
    pass


class GameNotStartedError(TileCrawlerError):
    """Raised when an action requires an active game but none exists."""
    pass


class NotInCombatError(TileCrawlerError):
    """Raised when a combat action is attempted outside combat."""
    pass


class CombatActiveError(TileCrawlerError):
    """Raised when an action is blocked because combat is in progress."""
    pass


class ItemNotFoundError(TileCrawlerError):
    """Raised when an item is not found in room or inventory."""
    pass


class InvalidDirectionError(TileCrawlerError):
    """Raised for invalid movement directions."""
    pass


class SessionNotFoundError(TileCrawlerError):
    """Raised when a session cannot be resolved."""
    pass


class NoExitError(TileCrawlerError):
    """Raised when attempting to move through a wall (no exit)."""
    pass


class RoomGenerationError(TileCrawlerError):
    """Raised when room generation fails."""
    pass
