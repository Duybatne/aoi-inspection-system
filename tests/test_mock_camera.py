import os
import sys
import logging
import numpy as np

# Ensure root directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.camera_drivers.mock_camera import MockCamera, MockCameraError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestMockCamera")

def test_camera_lifecycle():
    logger.info("Initializing mock camera...")
    cam = MockCamera(camera_id=0)
    
    # Assert initial states
    status = cam.get_status()
    assert not status["connected"]
    assert not status["grabbing"]
    
    # Test connection
    logger.info("Testing connection...")
    cam.connect()
    assert cam.is_connected
    
    # Test setting parameters
    logger.info("Testing parameter configuration...")
    cam.set_exposure(15000.0)
    cam.set_gain(6.0)
    status = cam.get_status()
    assert status["exposure_time_us"] == 15000.0
    assert status["gain_db"] == 6.0
    
    # Test grabbing
    logger.info("Testing start grabbing...")
    cam.start_grabbing()
    assert cam.is_grabbing
    
    # Test frame capture
    logger.info("Testing frame capture...")
    frame = cam.capture_frame(simulate_defects=True)
    
    # Verify image properties
    assert isinstance(frame, np.ndarray)
    logger.info(f"Captured frame shape: {frame.shape}")
    assert frame.shape == (2500, 4000, 3)  # Height, Width, Channels
    
    # Test stop grabbing & disconnect
    logger.info("Testing teardown...")
    cam.stop_grabbing()
    assert not cam.is_grabbing
    
    cam.disconnect()
    assert not cam.is_connected
    
    logger.info("All mock camera lifecycle tests PASSED!")

if __name__ == "__main__":
    test_camera_lifecycle()
