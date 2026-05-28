from fastapi import APIRouter, status
from models.schemas import HealthResponse

API_VERSION = "1.0.0"

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, status_code=200, summary="Health check")
async def health_check() -> HealthResponse:
    """Simple liveness check - no external calls, safe to poll frequently."""
    return HealthResponse(status="ok", version=API_VERSION)
