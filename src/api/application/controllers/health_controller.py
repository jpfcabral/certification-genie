"""Health check controller.

Provides a simple health check endpoint for monitoring and liveness probes.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return health status of the application."""
    return {"status": "healthy"}
