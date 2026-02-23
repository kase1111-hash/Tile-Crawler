"""
Tile-Crawler Backend API

FastAPI application providing endpoints for the dungeon crawler game.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from dependencies import AUTH_ENABLED, WEBSOCKET_ENABLED, limiter
from exceptions import TileCrawlerError
from llm_engine import get_llm_engine
from routers import health, game, combat, inventory, interaction

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)
request_logger = logging.getLogger("tile_crawler.requests")


# =============================================================================
# API Tags
# =============================================================================

tags_metadata = [
    {"name": "Health", "description": "API health and status endpoints"},
    {"name": "Game Management", "description": "Start, save, and load game sessions"},
    {"name": "Movement", "description": "Move the player through the dungeon"},
    {"name": "Combat", "description": "Combat actions when fighting enemies"},
    {"name": "Inventory", "description": "Manage player inventory and items"},
    {"name": "Interaction", "description": "Interact with NPCs and the environment"},
]

if AUTH_ENABLED:
    tags_metadata.insert(0, {"name": "Authentication", "description": "User registration, login, and profile management"})

if WEBSOCKET_ENABLED:
    tags_metadata.append({"name": "WebSocket", "description": "Real-time game updates via WebSocket connection"})


# =============================================================================
# Application Setup
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    logger.info("Tile-Crawler Backend Starting...")
    logger.info("   LLM Available: %s", get_llm_engine().is_available())
    logger.info("   Auth: %s", "enabled" if AUTH_ENABLED else "disabled")
    logger.info("   WebSocket: %s", "enabled" if WEBSOCKET_ENABLED else "disabled")
    yield
    logger.info("Tile-Crawler Backend Shutting Down...")


app = FastAPI(
    title="Tile-Crawler API",
    description="An LLM-powered procedural dungeon crawler.",
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Rate limiter (auth endpoints)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Game-specific exception handler — returns 400 with structured error
@app.exception_handler(TileCrawlerError)
async def game_error_handler(request: Request, exc: TileCrawlerError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_type": type(exc).__name__},
    )


# Catch-all — log the real error, return a sanitized message
@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"},
    )


# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    request_logger.info(
        "%s %s %d %.2fs",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# =============================================================================
# Router Registration
# =============================================================================

app.include_router(health.router)
app.include_router(game.router)
app.include_router(combat.router)
app.include_router(inventory.router)
app.include_router(interaction.router)

if AUTH_ENABLED:
    from routers import auth
    app.include_router(auth.router)

if WEBSOCKET_ENABLED:
    from routers import websocket
    app.include_router(websocket.router)


# =============================================================================
# Entrypoint
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    uvicorn.run("main:app", host=host, port=port, reload=debug)
