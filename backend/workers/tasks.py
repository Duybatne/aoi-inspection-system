import logging
import cv2
cv2.setNumThreads(0)
import numpy as np
import datetime
import redis
import json
from backend.workers.celery_app import celery_app
from backend.database import SessionLocal
from backend.models.database import Inspection, Defect
from backend.services.storage import storage_service
from backend.config import settings

# Phase 4: real pipeline modules
from core.inference_engine.detector import DetectorFactory
from core.preprocessing.image_validator import ImageValidator
from core.preprocessing.pipeline import PreprocessingPipeline
from core.verdict_engine.engine import VerdictEngine
from core.calibration.camera_calibration import CameraCalibration

logger = logging.getLogger("CeleryTasks")

# Initialize Redis client for Pub/Sub notifications
redis_client = redis.Redis.from_url(settings.REDIS_URL)

# ---------------------------------------------------------------------------
# Singleton pipeline components (instantiated once per worker process)
# ---------------------------------------------------------------------------
_validator = ImageValidator(
    blur_threshold=settings.IMAGE_BLUR_THRESHOLD,
    brightness_min=settings.IMAGE_BRIGHTNESS_MIN,
    brightness_max=settings.IMAGE_BRIGHTNESS_MAX,
)
_preprocessor = PreprocessingPipeline(target_size=(640, 640), apply_clahe=True)
_verdict_engine = VerdictEngine()
_calibration = CameraCalibration.load()   # passthrough-safe if no calibration file


def publish_event(event_name: str, data: dict):
    try:
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                return super().default(obj)

        payload = {"event": event_name, "data": data}
        redis_client.publish("aoi_events", json.dumps(payload, cls=DateTimeEncoder))
        logger.info(f"Published event '{event_name}' to Redis Pub/Sub.")
    except Exception as e:
        logger.error(f"Failed to publish event to Redis: {e}")


@celery_app.task(name="backend.workers.tasks.run_inspection_task")
def run_inspection_task(inspection_id: int, file_name: str) -> dict:
    """
    Phase 4 inspection pipeline:
        1. Fetch image from MinIO
        2. Decode + undistort (calibration)
        3. Validate image quality
        4. Preprocess (letterbox + CLAHE)
        5. Run inference (Roboflow cloud or Mock fallback)
        6. Evaluate verdict (rule-based engine)
        7. Persist defects + update inspection status
        8. Publish real-time WebSocket event
    """
    logger.info(f"[Task {inspection_id}] Starting Phase 4 inspection pipeline for file: {file_name}")
    db = SessionLocal()
    try:
        # --- Fetch inspection record ---
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        if not inspection:
            logger.error(f"[Task {inspection_id}] Inspection not found in database.")
            return {"status": "error", "message": "Inspection not found"}

        inspection.status = "PROCESSING"
        inspection.updated_at = datetime.datetime.utcnow()
        db.commit()
        publish_event("inspection_processing", {
            "id": inspection.id,
            "board_id": inspection.board_id,
            "status": inspection.status,
            "updated_at": inspection.updated_at,
        })

        # --- Step 1: Download image from MinIO ---
        logger.info(f"[Task {inspection_id}] Downloading image from MinIO...")
        img_bytes = storage_service.download_image(file_name)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return _fail_task(db, inspection, "Failed to decode image from storage.", publish_event)

        # --- Step 2: Lens undistortion (calibration) ---
        img = _calibration.undistort(img)

        # --- Step 3: Image quality validation ---
        validation = _validator.validate(img)
        if not validation.ok:
            logger.warning(f"[Task {inspection_id}] Image validation failed: {validation.reason}")
            return _fail_task(
                db, inspection,
                f"Image quality check failed: {validation.reason}",
                publish_event,
                status="ERROR"
            )
        logger.info(f"[Task {inspection_id}] Image validated successfully.")

        # --- Step 4: Preprocessing ---
        processed_img = _preprocessor.run(img)
        logger.info(f"[Task {inspection_id}] Preprocessing done: shape={processed_img.shape}")

        # --- Step 5: Inference ---
        detector = DetectorFactory.create(settings)
        logger.info(f"[Task {inspection_id}] Running inference with {type(detector).__name__}...")
        detected_defects = detector.detect(processed_img)
        logger.info(f"[Task {inspection_id}] Inference complete: {len(detected_defects)} raw detections.")

        # --- Step 6: Verdict evaluation ---
        verdict_result = _verdict_engine.evaluate(
            defects=detected_defects,
            high_conf_threshold=settings.VERDICT_HIGH_CONF_THRESHOLD,
            max_defect_count=settings.VERDICT_MAX_DEFECT_COUNT,
        )
        logger.info(
            f"[Task {inspection_id}] Verdict: {verdict_result.verdict} "
            f"(severity={verdict_result.severity}, reason={verdict_result.reason})"
        )

        # --- Step 7: Persist defects + update inspection ---
        db.query(Defect).filter(Defect.inspection_id == inspection_id).delete()

        defect_records = []
        for d in detected_defects:
            defect_records.append(Defect(
                inspection_id=inspection_id,
                class_id=d["class_id"],
                class_name=d["class_name"],
                confidence=d["confidence"],
                x_min=d["x_min"],
                y_min=d["y_min"],
                x_max=d["x_max"],
                y_max=d["y_max"],
                status="unconfirmed",
            ))

        if defect_records:
            db.add_all(defect_records)

        inspection.status = verdict_result.verdict  # PASS / FAIL / WARNING
        inspection.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(inspection)

        presigned_url = storage_service.get_presigned_url(file_name)

        # --- Step 8: Publish completion event ---
        publish_event("inspection_completed", {
            "id": inspection.id,
            "board_id": inspection.board_id,
            "status": inspection.status,
            "severity": verdict_result.severity,
            "verdict_reason": verdict_result.reason,
            "image_url": presigned_url,
            "updated_at": inspection.updated_at,
            "defects": [
                {
                    "id": d.id,
                    "class_id": d.class_id,
                    "class_name": d.class_name,
                    "confidence": d.confidence,
                    "x_min": d.x_min,
                    "y_min": d.y_min,
                    "x_max": d.x_max,
                    "y_max": d.y_max,
                    "status": d.status,
                }
                for d in inspection.defects
            ],
        })

        logger.info(f"[Task {inspection_id}] Pipeline complete: {inspection.status}")
        return {
            "status": "success",
            "inspection_id": inspection_id,
            "verdict": inspection.status,
            "severity": verdict_result.severity,
            "defects_count": len(detected_defects),
        }

    except Exception as e:
        logger.error(f"[Task {inspection_id}] Unexpected error: {e}", exc_info=True)
        try:
            inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
            if inspection:
                inspection.status = "ERROR"
                inspection.updated_at = datetime.datetime.utcnow()
                db.commit()
                publish_event("inspection_error", {
                    "id": inspection.id,
                    "board_id": inspection.board_id,
                    "status": inspection.status,
                    "updated_at": inspection.updated_at,
                })
        except Exception:
            pass
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


def _fail_task(db, inspection, message: str, publish_fn, status: str = "ERROR") -> dict:
    """Helper to mark inspection as failed and publish error event."""
    inspection.status = status
    inspection.updated_at = datetime.datetime.utcnow()
    db.commit()
    publish_fn("inspection_error", {
        "id": inspection.id,
        "board_id": inspection.board_id,
        "status": inspection.status,
        "updated_at": inspection.updated_at,
        "reason": message,
    })
    return {"status": "error", "message": message}
