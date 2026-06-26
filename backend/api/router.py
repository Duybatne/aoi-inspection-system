from fastapi import APIRouter
from backend.api.endpoints import inspections

api_router = APIRouter()
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
