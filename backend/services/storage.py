import io
import os
import logging
import cloudinary
import cloudinary.uploader
import cloudinary.api
from backend.config import settings

logger = logging.getLogger("StorageService")


def _init_cloudinary():
    """Configure Cloudinary from env settings. Returns True if configured."""
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        return True
    return False


class StorageService:
    """
    Unified storage service.
    - Production (cloud): Cloudinary (CLOUDINARY_* env vars set)
    - Local development fallback: /tmp/aoi_images/
    """

    def __init__(self):
        self.use_cloudinary = _init_cloudinary()
        if self.use_cloudinary:
            logger.info("StorageService: using Cloudinary backend.")
        else:
            logger.warning(
                "StorageService: CLOUDINARY_* env vars not set — "
                "falling back to local /tmp/aoi_images/ storage."
            )

    # ------------------------------------------------------------------
    # Public API (same interface as previous MinIO implementation)
    # ------------------------------------------------------------------

    def upload_image(self, file_name: str, data: bytes, content_type: str = "image/png") -> str:
        """Upload image bytes and return the storage key / public_id."""
        if self.use_cloudinary:
            return self._cloudinary_upload(file_name, data)
        return self._local_upload(file_name, data)

    def get_presigned_url(self, file_name: str, expires_minutes: int = 120) -> str:
        """Return a publicly accessible URL for the stored image."""
        if self.use_cloudinary:
            return self._cloudinary_url(file_name)
        return f"/api/inspections/image/{file_name}"

    def download_image(self, file_name: str) -> bytes:
        """Download image bytes from storage."""
        if self.use_cloudinary:
            return self._cloudinary_download(file_name)
        return self._local_download(file_name)

    # ------------------------------------------------------------------
    # Cloudinary implementations
    # ------------------------------------------------------------------

    def _cloudinary_upload(self, file_name: str, data: bytes) -> str:
        """Upload to Cloudinary. Returns public_id (= file_name without extension)."""
        # Cloudinary public_id should not contain dots; strip extension
        public_id = os.path.splitext(file_name)[0]
        folder = "aoi-pcb-images"
        try:
            result = cloudinary.uploader.upload(
                io.BytesIO(data),
                public_id=f"{folder}/{public_id}",
                resource_type="image",
                overwrite=True,
                invalidate=True,
            )
            logger.info(f"Cloudinary upload OK: {result['secure_url']}")
            # Return the full public_id so we can retrieve the URL later
            return result["public_id"]
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            raise

    def _cloudinary_url(self, file_name: str) -> str:
        """Build Cloudinary delivery URL from public_id (stored as file_name)."""
        try:
            # If file_name is already a full public_id (contains 'aoi-pcb-images/')
            public_id = file_name if "/" in file_name else f"aoi-pcb-images/{os.path.splitext(file_name)[0]}"
            url, _ = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type="image",
                secure=True,
            )
            return url
        except Exception as e:
            logger.error(f"Cloudinary URL generation failed: {e}")
            return ""

    def _cloudinary_download(self, file_name: str) -> bytes:
        """Download image bytes via Cloudinary URL."""
        import requests as req_lib
        url = self._cloudinary_url(file_name)
        if not url:
            raise RuntimeError(f"Cannot resolve Cloudinary URL for: {file_name}")
        resp = req_lib.get(url, timeout=15)
        resp.raise_for_status()
        return resp.content

    # ------------------------------------------------------------------
    # Local /tmp fallback implementations
    # ------------------------------------------------------------------

    def _local_upload(self, file_name: str, data: bytes) -> str:
        os.makedirs("/tmp/aoi_images", exist_ok=True)
        path = os.path.join("/tmp/aoi_images", file_name)
        with open(path, "wb") as f:
            f.write(data)
        logger.info(f"Local upload OK: {path}")
        return file_name

    def _local_download(self, file_name: str) -> bytes:
        path = os.path.join("/tmp/aoi_images", file_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Local file not found: {path}")
        with open(path, "rb") as f:
            return f.read()


storage_service = StorageService()
