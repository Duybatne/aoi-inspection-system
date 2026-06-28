import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.database import init_db
from backend.api.router import api_router
from backend.api.websocket import ws_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AOI_Backend")

app = FastAPI(
    title="AOI Automated Optical Inspection System API",
    version="1.0.0",
    description="Backend services for PCB inspection, defect detection, and reporting"
)

# CORS — allow Vercel frontend origin + localhost dev
origins = ["*"] if settings.FRONTEND_URL == "*" else [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

# Include API Routers
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "storage": "cloudinary" if settings.CLOUDINARY_CLOUD_NAME else "local",
    }

# Serve Frontend SPA (only in local dev — on Vercel the frontend is served directly)
import os
if os.path.isdir("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
