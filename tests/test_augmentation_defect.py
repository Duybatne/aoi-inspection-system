import os
import sys
import logging
import cv2

# Ensure root directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.camera_drivers.mock_camera import MockCamera
from data.synthetic_defect import SyntheticDefectGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAugmentationDefect")

def main():
    # Setup directories
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Initializing MockCamera and Capturing a Clean Board...")
    cam = MockCamera(camera_id=0)
    cam.connect()
    cam.start_grabbing()
    
    # Capture clean board without defects
    clean_board = cam.capture_frame(simulate_defects=False)
    cv2.imwrite(os.path.join(output_dir, "0_clean_board.png"), clean_board)
    logger.info("Saved clean board to output/0_clean_board.png")
    
    # Initialize generator
    generator = SyntheticDefectGenerator()
    
    # Grid coordinates calculation matching MockCamera grid layout
    # Width: 4000, Height: 2500, Cols: 8, Rows: 6
    width, height = 4000, 2500
    cols, rows = 8, 6
    x_step = (width - 200) // cols
    y_step = (height - 200) // rows
    
    def get_comp_bbox(c, r):
        cx = 100 + c * x_step + x_step // 2
        cy = 100 + r * y_step + y_step // 2
        comp_w, comp_h = 100, 60
        x1 = cx - comp_w // 2
        y1 = cy - comp_h // 2
        x2 = cx + comp_w // 2
        y2 = cy + comp_h // 2
        return x1, y1, x2, y2

    # 1. Generate Missing Component Defect at Grid (1, 1)
    bbox_missing = get_comp_bbox(1, 1)
    missing_img = generator.generate_missing(clean_board, bbox_missing)
    cv2.imwrite(os.path.join(output_dir, "1_missing_component.png"), missing_img)
    logger.info("Generated and saved missing component defect to output/1_missing_component.png")
    
    # 2. Generate Misaligned Component Defect at Grid (3, 2)
    bbox_misaligned = get_comp_bbox(3, 2)
    misaligned_img = generator.generate_misaligned(clean_board, bbox_misaligned, shift=(20, -15), angle=12.0)
    cv2.imwrite(os.path.join(output_dir, "2_misaligned_component.png"), misaligned_img)
    logger.info("Generated and saved misaligned component defect to output/2_misaligned_component.png")
    
    # 3. Generate Solder Bridge Defect between pads at Grid (5, 4)
    # Pads are at cx - gap//2 and cx + gap//2
    # Gap is 80.
    cx = 100 + 5 * x_step + x_step // 2
    cy = 100 + 4 * y_step + y_step // 2
    gap = 80
    pad1 = (cx - gap // 2, cy)
    pad2 = (cx + gap // 2, cy)
    
    bridge_img = generator.generate_solder_bridge(clean_board, pad1, pad2, thickness=12)
    cv2.imwrite(os.path.join(output_dir, "3_solder_bridge.png"), bridge_img)
    logger.info("Generated and saved solder bridge defect to output/3_solder_bridge.png")
    
    # Teardown camera
    cam.stop_grabbing()
    cam.disconnect()
    
    logger.info(f"All synthetic defect generation tests completed! Files saved in: {output_dir}")

if __name__ == "__main__":
    main()
