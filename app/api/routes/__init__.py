from app.api.routes.auth import router as auth_router
from app.api.routes.feed import router as feed_router
from app.api.routes.health import router as health_router
from app.api.routes.videos import router as videos_router

__all__ = ["auth_router", "feed_router", "health_router", "videos_router"]
