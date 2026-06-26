import uuid
import logging
import cv2
import numpy as np
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.database import Inspection, Defect
from backend.models.schemas import InspectionCreate, InspectionResponse, OverrideRequest
from backend.services.storage import storage_service
from backend.config import settings
from hardware.camera_drivers.camera_factory import CameraFactory, CameraNotAvailableError
from backend.workers.tasks import run_inspection_task

logger = logging.getLogger("InspectionsEndpoint")

router = APIRouter()


def _create_pending_inspection(db: Session, board_id: str, file_name: str) -> Inspection:
    """Helper: upload to MinIO, create PENDING record, return it."""
    presigned_url = storage_service.get_presigned_url(file_name)
    inspection = Inspection(board_id=board_id, status="PENDING", image_url=presigned_url)
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.post("/trigger", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def trigger_inspection(payload: InspectionCreate, db: Session = Depends(get_db)):
    """
    Triggers a new PCB inspection using the configured camera (default: MockCamera).
    1. Connects to camera via CameraFactory
    2. Captures a frame
    3. Uploads to MinIO
    4. Creates PENDING inspection record
    5. Dispatches Celery worker for inference
    """
    try:
        cam = CameraFactory.create(settings.CAMERA_TYPE, settings.CAMERA_ID)
    except CameraNotAvailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    try:
        cam.connect()
        cam.start_grabbing()
        frame = cam.capture_frame(simulate_defects=True)

        _, encoded_img = cv2.imencode(".png", frame)
        img_bytes = encoded_img.tobytes()

        file_name = f"{payload.board_id}_{uuid.uuid4().hex[:8]}.png"
        storage_service.upload_image(file_name, img_bytes)

        inspection = _create_pending_inspection(db, payload.board_id, file_name)
        run_inspection_task.delay(inspection.id, file_name)

        logger.info(f"Triggered async inspection {inspection.id} (PENDING) via camera capture.")
        return inspection

    except Exception as e:
        logger.error(f"Error during camera-triggered inspection: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inspection trigger failed: {str(e)}"
        )
    finally:
        try:
            cam.stop_grabbing()
            cam.disconnect()
        except Exception:
            pass


@router.post("/upload", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
async def upload_inspection(
    board_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a pre-captured PCB image for inspection (no camera required).

    Accepts JPEG or PNG image via multipart form.
    Ideal for testing with real images without physical camera hardware.

    Form fields:
        board_id  — PCB serial number / barcode
        file      — PCB image (JPEG or PNG)
    """
    # Validate MIME type
    allowed_types = {"image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Use JPEG or PNG."
        )

    try:
        img_bytes = await file.read()

        # Decode to validate it is a real image
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not decode uploaded file as an image."
            )

        # Re-encode as PNG for consistent storage format
        _, encoded_img = cv2.imencode(".png", img)
        png_bytes = encoded_img.tobytes()

        file_name = f"{board_id}_{uuid.uuid4().hex[:8]}.png"
        storage_service.upload_image(file_name, png_bytes)

        inspection = _create_pending_inspection(db, board_id, file_name)
        run_inspection_task.delay(inspection.id, file_name)

        logger.info(
            f"Triggered async inspection {inspection.id} (PENDING) via image upload "
            f"[{file.filename}, {len(img_bytes)} bytes, {img.shape[1]}x{img.shape[0]}px]."
        )
        return inspection

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing uploaded image: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload inspection failed: {str(e)}"
        )


@router.get("/", response_model=List[InspectionResponse])
def list_inspections(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieves all inspection records paginated."""
    inspections = db.query(Inspection).order_by(Inspection.created_at.desc()).offset(skip).limit(limit).all()
    for insp in inspections:
        if insp.image_url:
            file_name = insp.image_url.split("/")[-1].split("?")[0]
            insp.image_url = storage_service.get_presigned_url(file_name)
    return inspections


@router.get("/{inspection_id}", response_model=InspectionResponse)
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    """Retrieves detailed inspection report by ID."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    if inspection.image_url:
        file_name = inspection.image_url.split("/")[-1].split("?")[0]
        inspection.image_url = storage_service.get_presigned_url(file_name)
    return inspection


@router.post("/{inspection_id}/override", response_model=InspectionResponse)
def override_verdict(inspection_id: int, payload: OverrideRequest, db: Session = Depends(get_db)):
    """Allows an operator to override an inspection verdict."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    inspection.operator_override = True
    inspection.operator_verdict = payload.operator_verdict
    inspection.operator_notes = payload.operator_notes
    inspection.status = payload.operator_verdict
    db.commit()
    db.refresh(inspection)
    return inspection


@router.delete("/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inspection(inspection_id: int, db: Session = Depends(get_db)):
    """Deletes an inspection record and its defects cascade."""
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    db.delete(inspection)
    db.commit()
    return None
