# API routers package

from app.routers.auth import router as auth_router
from app.routers.weather import router as weather_router

# Re-export for easy importing
auth = auth_router
weather = weather_router
