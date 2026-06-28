import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # System Configuration
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "aoi_user"
    DB_PASSWORD: str = "aoi_password"
    DB_NAME: str = "aoi_db"
    DATABASE_URL: Optional[str] = None

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: Optional[str] = None

    # RabbitMQ & Celery
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "aoi_mq_user"
    RABBITMQ_PASSWORD: str = "aoi_mq_password"
    CELERY_BROKER_URL: Optional[str] = None

    # Cloudinary Configuration (replaces MinIO for cloud deployment)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # CORS — frontend URL (e.g. https://your-app.vercel.app)
    FRONTEND_URL: str = "*"

    # Hardware Configuration
    CAMERA_TYPE: str = "mock"
    CAMERA_ID: int = 0
    LIGHTING_PORT: str = "/dev/ttyUSB0"
    LIGHTING_BAUDRATE: int = 9600

    # AI Model Configuration (local — legacy)
    YOLO_MODEL_PATH: str = "ml/models/yolov11-m.engine"
    CONFIDENCE_THRESHOLD: float = 0.5
    RECALL_MIN_THRESHOLD: float = 0.95

    # Cloud Inference (Roboflow)
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_MODEL_ID: str = "pcb-defect-detection/1"
    ROBOFLOW_API_URL: str = "https://detect.roboflow.com"

    # Verdict Engine
    VERDICT_HIGH_CONF_THRESHOLD: float = 0.85
    VERDICT_MAX_DEFECT_COUNT: int = 3

    # Image Validation
    IMAGE_BLUR_THRESHOLD: float = 100.0
    IMAGE_BRIGHTNESS_MIN: float = 30.0
    IMAGE_BRIGHTNESS_MAX: float = 230.0

    # Autopopulate Database/Broker URLs if not explicitly defined
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        if not self.REDIS_URL:
            self.REDIS_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"

settings = Settings()
