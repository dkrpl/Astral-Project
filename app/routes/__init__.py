from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.systems import router as systems_router
from app.routes.chat import router as chat_router
from app.routes.admin import router as admin_router

__all__ = ["auth_router", "users_router", "systems_router", "chat_router", "admin_router"]