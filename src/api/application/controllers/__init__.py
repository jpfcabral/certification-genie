"""Controllers package for the Certification Genie API.

Exposes the webhook and health routers for inclusion in the FastAPI app.
"""

from src.api.application.controllers.health_controller import router as health_router
from src.api.application.controllers.webhook_controller import router as webhook_router

__all__ = ["webhook_router", "health_router"]
