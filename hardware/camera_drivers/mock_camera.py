import time
import logging
import random
import threading
import os
import json
from typing import Tuple, Dict, Any, Optional
import numpy as np
import cv2
from hardware.camera_drivers.base_camera import BaseCamera

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MockCamera")

class MockCameraError(Exception):
    """Custom exception for mock camera errors."""
    pass

class MockCamera(BaseCamera):
    """
    MockCamera simulates an industrial GigE Vision camera (e.g., Basler)
    for development, testing, and CI/CD pipelines without physical hardware.
    """
    def __init__(self, camera_id: int = 0):
        self.camera_id = camera_id
        self.is_connected = False
        self.is_grabbing = False
        
        # Camera Settings
        self.exposure_time = 20000.0  # microseconds
        self.gain = 0.0               # dB
        self.frame_rate = 10.0        # FPS
        self.width = 4000             # standard 10MP resolution (e.g., 4000x2500)
        self.height = 2500
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Defect probability for simulated frames
        self.defect_probability = 0.3
        self.last_defects = []

    def connect(self) -> bool:
        """Simulate connecting to the physical GigE camera."""
        with self._lock:
            if self.is_connected:
                logger.warning("Camera already connected.")
                return True
            
            logger.info(f"Connecting to GigE Camera ID: {self.camera_id}...")
            time.sleep(0.5)  # Simulate network latency
            self.is_connected = True
            logger.info("Camera connected successfully.")
            return True

    def disconnect(self) -> bool:
        """Simulate disconnecting from the camera."""
        with self._lock:
            if not self.is_connected:
                logger.warning("Camera already disconnected.")
                return True
            
            if self.is_grabbing:
                self.stop_grabbing()
                
            logger.info("Disconnecting camera...")
            time.sleep(0.2)
            self.is_connected = False
            logger.info("Camera disconnected successfully.")
            return True

    def start_grabbing(self) -> bool:
        """Start acquisition loop."""
        with self._lock:
            if not self.is_connected:
                raise MockCameraError("Cannot start grabbing. Camera is not connected.")
            if self.is_grabbing:
                return True
            
            logger.info("Start image acquisition loop...")
            self.is_grabbing = True
            return True

    def stop_grabbing(self) -> bool:
        """Stop acquisition loop."""
        with self._lock:
            if not self.is_grabbing:
                return True
            
            logger.info("Stopping image acquisition loop...")
            self.is_grabbing = False
            return True

    def set_exposure(self, exposure_time: float) -> None:
        """Set exposure time in microseconds."""
        with self._lock:
            if exposure_time <= 0:
                raise ValueError("Exposure time must be positive.")
            self.exposure_time = exposure_time
            logger.info(f"Exposure set to {self.exposure_time} us.")

    def set_gain(self, gain: float) -> None:
        """Set gain in dB."""
        with self._lock:
            if gain < 0:
                raise ValueError("Gain cannot be negative.")
            self.gain = gain
            logger.info(f"Gain set to {self.gain} dB.")

    def capture_frame(self, simulate_defects: bool = True) -> np.ndarray:
        """
        Capture a single frame. Simulates high-resolution PCB image generation.
        Returns:
            np.ndarray: BGR image representing a PCB.
        """
        if not self.is_connected:
            raise MockCameraError("Cannot capture. Camera is not connected.")
        if not self.is_grabbing:
            raise MockCameraError("Cannot capture. Acquisition loop is not running.")
            
        logger.info(f"Triggering frame acquisition (Exposure: {self.exposure_time}us, Gain: {self.gain}dB)...")
        # Simulate sensor readout latency
        sleep_time = max(0.01, self.exposure_time / 1_000_000.0)
        time.sleep(sleep_time)
        
        pcb = self._generate_synthetic_pcb(simulate_defects)
        
        # Save defects to a temporary JSON file at the project root for the ML detector fallback to read
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filepath = os.path.join(root_dir, ".mock_defects.json")
            with open(filepath, "w") as f:
                json.dump(self.last_defects, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to write mock defects to file: {e}")
            
        return pcb

    def _generate_synthetic_pcb(self, simulate_defects: bool) -> np.ndarray:
        """
        Generates a synthetic PCB image with green background, gold traces,
        and multiple components. May randomly introduce defects.
        """
        # Create green PCB board background
        # H: 35-45 (Green-Yellowish in OpenCV BGR)
        # We will use direct BGR colors: Green is around (34, 120, 45)
        pcb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        pcb[:, :] = [30, 90, 20]  # dark green
        
        # Add some random board textures/fibers
        noise = np.random.randint(0, 15, (self.height, self.width, 3), dtype=np.uint8)
        pcb = cv2.add(pcb, noise)
        
        # Draw some gold traces and pads
        # Golden BGR color: (0, 190, 230)
        gold_color = (15, 180, 210)
        
        # Simulated components layout: grid of components
        # X range: 100 to width-100, Y range: 100 to height-100
        cols, rows = 8, 6
        x_step = (self.width - 200) // cols
        y_step = (self.height - 200) // rows
        
        self.last_defects = []
        has_defect = simulate_defects and (random.random() < self.defect_probability)
        defect_type = None
        defect_loc = (0, 0)
        
        if has_defect:
            defect_types = ["missing", "misaligned", "tombstone", "bridge"]
            defect_type = random.choice(defect_types)
            defect_loc = (random.randint(0, cols - 1), random.randint(0, rows - 1))
            logger.info(f"Simulating defect: '{defect_type}' at component grid {defect_loc}")
            
            c, r = defect_loc
            cx = 100 + c * x_step + x_step // 2
            cy = 100 + r * y_step + y_step // 2
            comp_w, comp_h = 100, 60
            gap = 80
            
            if defect_type == "missing":
                x_min = cx - comp_w // 2
                y_min = cy - comp_h // 2
                x_max = cx + comp_w // 2
                y_max = cy + comp_h // 2
                class_id = 0
            elif defect_type == "misaligned":
                x_min = cx - comp_w // 2 - 25
                y_min = cy - comp_h // 2 - 15
                x_max = cx + comp_w // 2 + 25
                y_max = cy + comp_h // 2 + 15
                class_id = 2
            elif defect_type == "tombstone":
                x_min = cx - gap // 2 - comp_h // 2
                y_min = cy - comp_w // 2
                x_max = cx - gap // 2 + comp_h // 2
                y_max = cy + comp_w // 2
                class_id = 4
            else:  # bridge / solder_bridge
                x_min = cx - gap // 2
                y_min = cy - 30
                x_max = cx + gap // 2
                y_max = cy + 30
                class_id = 1
                
            self.last_defects.append({
                "class_id": class_id,
                "class_name": defect_type,
                "confidence": round(random.uniform(0.85, 0.98), 2),
                "x_min": float(x_min),
                "y_min": float(y_min),
                "x_max": float(x_max),
                "y_max": float(y_max)
            })

        for r in range(rows):
            for c in range(cols):
                cx = 100 + c * x_step + x_step // 2
                cy = 100 + r * y_step + y_step // 2
                
                # Draw pad pairs
                pad_w, pad_h = 60, 40
                gap = 80
                cv2.rectangle(pcb, (cx - gap//2 - pad_w, cy - pad_h//2), (cx - gap//2, cy + pad_h//2), gold_color, -1)
                cv2.rectangle(pcb, (cx + gap//2, cy - pad_h//2), (cx + gap//2 + pad_w, cy + pad_h//2), gold_color, -1)
                
                # Draw connecting traces
                cv2.line(pcb, (cx - gap//2 - pad_w, cy), (cx - gap//2 - pad_w - 50, cy), gold_color, 4)
                cv2.line(pcb, (cx + gap//2 + pad_w, cy), (cx + gap//2 + pad_w + 50, cy), gold_color, 4)

                # Skip drawing component if missing defect
                if has_defect and defect_type == "missing" and (c, r) == defect_loc:
                    continue

                # Component offset for alignment defect
                ox, oy = 0, 0
                angle = 0
                if has_defect and (c, r) == defect_loc:
                    if defect_type == "misaligned":
                        ox = random.choice([-25, 25])
                        oy = random.choice([-15, 15])
                    elif defect_type == "tombstone":
                        # Draw component standing on one pad (narrower width, shift to one side)
                        ox = -gap // 2
                        angle = 45 # tilted
                    elif defect_type == "bridge":
                        # Draw a solder blob bridging the pads
                        solder_color = (180, 180, 180) # silver
                        cv2.circle(pcb, (cx, cy), 30, solder_color, -1)

                # Draw component body (typically black or gray rectangle)
                comp_w, comp_h = 100, 60
                comp_color = (40, 40, 40) # dark gray
                
                # Draw component with rotation and translation
                rect = ((cx + ox, cy + oy), (comp_w, comp_h), angle)
                box = cv2.boxPoints(rect)
                box = np.intp(box)
                cv2.drawContours(pcb, [box], 0, comp_color, -1)
                
                # Draw metal endcaps
                cap_w = 15
                cap_color = (200, 200, 200) # silver/white
                # Left cap
                left_rect = ((cx - comp_w//2 + cap_w//2 + ox, cy + oy), (cap_w, comp_h), angle)
                left_box = cv2.boxPoints(left_rect)
                cv2.drawContours(pcb, [np.intp(left_box)], 0, cap_color, -1)
                # Right cap
                right_rect = ((cx + comp_w//2 - cap_w//2 + ox, cy + oy), (cap_w, comp_h), angle)
                right_box = cv2.boxPoints(right_rect)
                cv2.drawContours(pcb, [np.intp(right_box)], 0, cap_color, -1)

        # Apply slight lens blur to simulate optical properties
        pcb = cv2.GaussianBlur(pcb, (3, 3), 0)
        
        # Add slight white noise to simulate sensor gain
        if self.gain > 0:
            noise_sigma = self.gain * 2.0
            gauss = np.random.normal(0, noise_sigma, (self.height, self.width, 3)).astype(np.float32)
            pcb_float = pcb.astype(np.float32) + gauss
            pcb = np.clip(pcb_float, 0, 255).astype(np.uint8)

        return pcb

    def get_status(self) -> Dict[str, Any]:
        """Return current status of the camera."""
        with self._lock:
            return {
                "camera_id": self.camera_id,
                "connected": self.is_connected,
                "grabbing": self.is_grabbing,
                "exposure_time_us": self.exposure_time,
                "gain_db": self.gain,
                "frame_rate_fps": self.frame_rate,
                "resolution": f"{self.width}x{self.height}"
            }
