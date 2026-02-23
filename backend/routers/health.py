"""Health check endpoint."""

from fastapi import APIRouter

from llm_engine import get_llm_engine
from session_manager import get_session_manager
from schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="API health check",
    description="Health check including LLM availability status."
)
async def health_check():
    """API health check."""
    llm_available = get_llm_engine().is_available()
    session_count = await get_session_manager().get_session_count()

    return HealthResponse(
        status="healthy" if llm_available else "degraded",
        llm_available=llm_available,
        version="0.1.0",
        active_sessions=session_count,
    )
