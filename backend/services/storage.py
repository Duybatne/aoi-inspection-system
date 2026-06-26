import io
import logging
from datetime import timedelta
from minio import Minio
from backend.config import settings

logger = logging.getLogger("StorageService")

class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET_NAME

    def upload_image(self, file_name: str, data: bytes, content_type: str = "image/png") -> str:
        """
        Uploads image data to MinIO bucket and returns the object name / path.
        """
        try:
            logger.info(f"Uploading file {file_name} to MinIO...")
            data_stream = io.BytesIO(data)
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=file_name,
                data=data_stream,
                length=len(data),
                content_type=content_type
            )
            logger.info(f"File {file_name} uploaded successfully.")
            return file_name
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            raise

    def get_presigned_url(self, file_name: str, expires_minutes: int = 120) -> str:
        """
        Generates a temporary pre-signed URL for browser viewing.
        """
        try:
            url = self.client.get_presigned_url(
                method="GET",
                bucket_name=self.bucket,
                object_name=file_name,
                expires=timedelta(minutes=expires_minutes)
            )
            return url
        except Exception as e:
            logger.error(f"Failed to get presigned URL: {e}")
            return f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}/{file_name}"

    def download_image(self, file_name: str) -> bytes:
        """
        Downloads image from MinIO bucket and returns raw bytes.
        """
        response = None
        try:
            response = self.client.get_object(
                bucket_name=self.bucket,
                object_name=file_name
            )
            return response.read()
        except Exception as e:
            logger.error(f"Failed to download image {file_name}: {e}")
            raise
        finally:
            if response:
                response.close()
                response.release_conn()
            
storage_service = StorageService()
