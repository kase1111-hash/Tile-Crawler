"""Health check endpoint."""

from fastapi import APIRouter

from llm_engine import get_llm_engine
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
    return HealthResponse(
        status="healthy",
        llm_available=get_llm_engine().is_available(),
        version="0.1.0"
    )
