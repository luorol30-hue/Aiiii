from fastapi import APIRouter

from app.api.routes import ai, auth, crops, farms, health, notifications, reports, satellite, weather

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(farms.router, prefix="/farms", tags=["farms"])
api_router.include_router(crops.router, prefix="/crops", tags=["crops"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(satellite.router, prefix="/satellite", tags=["satellite"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
