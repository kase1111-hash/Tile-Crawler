"""
LLM Latency Measurement for Tile-Crawler

Provides a decorator and context manager to log LLM call latency.
"""

import time
import logging
import functools
from typing import Callable

logger = logging.getLogger("llm_latency")


def timed_llm_call(label: str = ""):
    """Decorator that logs execution time for async LLM calls.

    Args:
        label: Human-readable label for the metric (e.g., "generate_room").
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.monotonic() - start
                name = label or func.__name__
                logger.info(f"LLM call [{name}] completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.monotonic() - start
                name = label or func.__name__
                logger.warning(f"LLM call [{name}] failed after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator


class LLMTimer:
    """Context manager for timing LLM calls inline."""

    def __init__(self, label: str = "llm_call"):
        self.label = label
        self.elapsed: float = 0.0

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.monotonic() - self._start
        if exc_type:
            logger.warning(f"LLM call [{self.label}] failed after {self.elapsed:.2f}s")
        else:
            logger.info(f"LLM call [{self.label}] completed in {self.elapsed:.2f}s")
        return False
