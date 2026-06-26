import os
import sys
import logging
import pytest
from fastapi.testclient import TestClient

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAPI")

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    logger.info("Testing health check endpoint...")
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    logger.info("Health check passed.")

def test_inspection_lifecycle(client):
    logger.info("Testing inspection triggering...")
    # Trigger an inspection for a board
    payload = {"board_id": "PCB-API-TEST-999"}
    response = client.post("/api/inspections/trigger", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["board_id"] == "PCB-API-TEST-999"
    assert data["status"] == "PENDING"
    inspection_id = data["id"]
    logger.info(f"Triggered inspection ID {inspection_id} with status: {data['status']}")

    # Get the triggered inspection
    logger.info(f"Retrieving inspection {inspection_id}...")
    response = client.get(f"/api/inspections/{inspection_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == inspection_id

    # List all inspections
    logger.info("Listing all inspections...")
    response = client.get("/api/inspections/")
    assert response.status_code == 200
    inspections_list = response.json()
    assert len(inspections_list) > 0
    assert any(x["id"] == inspection_id for x in inspections_list)

    # Test override
    logger.info(f"Testing operator override on inspection {inspection_id}...")
    override_payload = {
        "operator_verdict": "PASS",
        "operator_notes": "False positive, golden PCB confirmed manually"
    }
    response = client.post(f"/api/inspections/{inspection_id}/override", json=override_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["operator_override"] is True
    assert data["operator_verdict"] == "PASS"
    assert data["status"] == "PASS"

    # Test delete
    logger.info(f"Testing deletion of inspection {inspection_id}...")
    response = client.delete(f"/api/inspections/{inspection_id}")
    assert response.status_code == 204

    # Verify deleted
    response = client.get(f"/api/inspections/{inspection_id}")
    assert response.status_code == 404
    logger.info("Inspection lifecycle test passed.")


def test_upload_valid_image(client):
    """POST /api/inspections/upload with a valid PNG returns 201 PENDING."""
    import io
    import numpy as np
    import cv2

    # Synthesize a small valid PNG in memory
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:80, 20:80] = (0, 180, 90)  # add some colour
    _, encoded = cv2.imencode(".png", img)
    img_bytes = encoded.tobytes()

    response = client.post(
        "/api/inspections/upload",
        data={"board_id": "PCB-UPLOAD-TEST-001"},
        files={"file": ("test_pcb.png", io.BytesIO(img_bytes), "image/png")},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["board_id"] == "PCB-UPLOAD-TEST-001"
    assert data["status"] == "PENDING"
    logger.info(f"Upload test: inspection {data['id']} created in PENDING state.")

    # Cleanup
    client.delete(f"/api/inspections/{data['id']}")


def test_upload_invalid_mime_type(client):
    """POST /api/inspections/upload with text/plain must return 400."""
    import io

    response = client.post(
        "/api/inspections/upload",
        data={"board_id": "PCB-INVALID-MIME"},
        files={"file": ("not_an_image.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()
    logger.info("Invalid MIME type correctly rejected with 400.")


def test_upload_corrupt_image(client):
    """POST /api/inspections/upload with corrupt bytes must return 400."""
    import io

    response = client.post(
        "/api/inspections/upload",
        data={"board_id": "PCB-CORRUPT"},
        files={"file": ("corrupt.png", io.BytesIO(b"\x89PNG\r\n\x1a\ngarbage"), "image/png")},
    )
    assert response.status_code == 400
    assert "decode" in response.json()["detail"].lower()
    logger.info("Corrupt image bytes correctly rejected with 400.")


if __name__ == "__main__":
    try:
        with TestClient(app) as client:
            test_health_check(client)
            test_inspection_lifecycle(client)
        logger.info("All API integration tests passed successfully!")
    except Exception as e:
        logger.error(f"API test failed: {e}")
        sys.exit(1)
