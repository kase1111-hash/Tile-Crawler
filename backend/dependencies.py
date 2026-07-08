"""
Shared dependencies and feature flags for Tile-Crawler.
"""

import os

from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import get_current_user_optional

load_dotenv()

# Feature flags
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"

# Rate limiting. Every keypress in the client is an API call (moves also
# fire a prefetch), so the game limit must comfortably exceed human APM —
# 60/minute produced 429s during normal exploration.
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "10/minute")
RATE_LIMIT_GAME = os.getenv("RATE_LIMIT_GAME", "300/minute")
limiter = Limiter(key_func=get_remote_address)

# Auth dependency: resolves to User or None depending on AUTH_ENABLED
if AUTH_ENABLED:
    get_optional_user = get_current_user_optional
else:
    async def get_optional_user():
        return None
