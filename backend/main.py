import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.database import init_db
from backend.api.router import api_router
from backend.api.websocket import ws_router
from minio import Minio

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

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # 1. Initialize Database Tables
    init_db()
    
    # 2. Initialize MinIO bucket
    try:
        logger.info("Initializing MinIO storage bucket...")
        # Since we use Minio SDK, let's create a client connection
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        if not client.bucket_exists(settings.MINIO_BUCKET_NAME):
            client.make_bucket(settings.MINIO_BUCKET_NAME)
            logger.info(f"Created MinIO bucket: {settings.MINIO_BUCKET_NAME}")
        else:
            logger.info(f"MinIO bucket {settings.MINIO_BUCKET_NAME} already exists.")
    except Exception as e:
        logger.error(f"Error initializing MinIO bucket: {e}")

# Include API Routers
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "storage": "connected"
    }

# Serve Frontend SPA
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

