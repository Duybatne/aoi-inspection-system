import random
import logging
from typing import Tuple, List, Dict, Any
import numpy as np
import cv2

logger = logging.getLogger("SyntheticDefectGenerator")

class SyntheticDefectGenerator:
    """
    SyntheticDefectGenerator generates realistic artificial defects on clean PCB images.
    Used for data augmentation to resolve class imbalance (DR-004 / DR-005).
    """
    def __init__(self, board_color: Tuple[int, int, int] = (30, 90, 20)):
        self.board_color = board_color  # default dark green BGR

    def generate_missing(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Simulates missing component defect by filling the bounding box with the board color.
        Args:
            image: np.ndarray (BGR)
            bbox: (x_min, y_min, x_max, y_max) of the component
        """
        img_out = image.copy()
        x1, y1, x2, y2 = bbox
        
        # Crop surrounding green texture to fill realistically instead of solid color
        h, w, _ = image.shape
        pad = 20
        # Determine source region for green texture (offset slightly from the component)
        src_x1 = max(0, x1 - 100)
        src_y1 = max(0, y1 - 100)
        src_x2 = max(0, x1 - pad)
        src_y2 = max(0, y1 - pad)
        
        # Fallback to solid color if texture crop is invalid
        if (src_x2 - src_x1) > 10 and (src_y2 - src_y1) > 10:
            texture = image[src_y1:src_y2, src_x1:src_x2]
            texture_resized = cv2.resize(texture, (x2 - x1, y2 - y1))
            img_out[y1:y2, x1:x2] = texture_resized
        else:
            cv2.rectangle(img_out, (x1, y1), (x2, y2), self.board_color, -1)
            
        # Add slight Gaussian noise to make it blend in
        noise = np.random.normal(0, 3, (y2 - y1, x2 - x1, 3)).astype(np.uint8)
        img_out[y1:y2, x1:x2] = cv2.add(img_out[y1:y2, x1:x2], noise)
        
        return img_out

    def generate_misaligned(
        self, 
        image: np.ndarray, 
        bbox: Tuple[int, int, int, int], 
        shift: Tuple[int, int] = (15, 10),
        angle: float = 8.0
    ) -> np.ndarray:
        """
        Simulates misaligned component defect by cropping, filling original area, 
        and pasting shifted + rotated component.
        Args:
            image: np.ndarray (BGR)
            bbox: (x_min, y_min, x_max, y_max)
            shift: (dx, dy) translation offset in pixels
            angle: rotation angle in degrees
        """
        x1, y1, x2, y2 = bbox
        h, w, _ = image.shape
        
        # Crop component body
        comp = image[y1:y2, x1:x2].copy()
        
        # Fill the original location with background board texture
        img_out = self.generate_missing(image, bbox)
        
        # Create larger canvas to rotate component without clipping
        cw, ch = (x2 - x1), (y2 - y1)
        canvas_h, canvas_w = ch * 2, cw * 2
        canvas = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
        
        # Put component in center with alpha channel (mask)
        canvas[ch//2 : ch//2 + ch, cw//2 : cw//2 + cw, :3] = comp
        canvas[ch//2 : ch//2 + ch, cw//2 : cw//2 + cw, 3] = 255
        
        # Rotate canvas
        center = (canvas_w // 2, canvas_h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(canvas, rot_mat, (canvas_w, canvas_w), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
        
        # Calculate target position with shift
        dx, dy = shift
        target_cx = (x1 + x2) // 2 + dx
        target_cy = (y1 + y2) // 2 + dy
        
        # Paste rotated component back using alpha blending
        rx1 = max(0, target_cx - canvas_w // 2)
        ry1 = max(0, target_cy - canvas_h // 2)
        rx2 = min(w, target_cx + canvas_w // 2)
        ry2 = min(h, target_cy + canvas_h // 2)
        
        # Crop overlapping part on canvas
        cx1 = max(0, canvas_w // 2 - (target_cx - rx1))
        cy1 = max(0, canvas_h // 2 - (target_cy - ry1))
        cx2 = cx1 + (rx2 - rx1)
        cy2 = cy1 + (ry2 - ry1)
        
        if (rx2 - rx1) > 0 and (ry2 - ry1) > 0:
            roi = img_out[ry1:ry2, rx1:rx2]
            patch = rotated[cy1:cy2, cx1:cx2]
            
            mask = patch[:, :, 3:] / 255.0
            img_out[ry1:ry2, rx1:rx2] = (roi * (1.0 - mask) + patch[:, :, :3] * mask).astype(np.uint8)

        return img_out

    def generate_solder_bridge(
        self, 
        image: np.ndarray, 
        pt1: Tuple[int, int], 
        pt2: Tuple[int, int], 
        thickness: int = 15
    ) -> np.ndarray:
        """
        Simulates solder bridge defect by drawing a silvery metallic blob connecting two points.
        """
        img_out = image.copy()
        
        # Draw base connection line representing main short
        solder_color = (195, 200, 202) # silver gray
        cv2.line(img_out, pt1, pt2, solder_color, thickness, lineType=cv2.LINE_AA)
        
        # Draw organic irregular shape (soldering flow isn't perfectly straight)
        mid_x = (pt1[0] + pt2[0]) // 2
        mid_y = (pt1[1] + pt2[1]) // 2
        
        # Draw central blob
        cv2.circle(img_out, (mid_x, mid_y), int(thickness * 1.3), solder_color, -1)
        # Add shininess/reflection highlight
        highlight_color = (240, 242, 245)
        cv2.circle(img_out, (mid_x - thickness//4, mid_y - thickness//4), int(thickness * 0.4), highlight_color, -1)
        
        # Add slight shadow to make it look 3D
        shadow_color = (10, 30, 10)
        mask = np.zeros_like(image)
        cv2.line(mask, pt1, pt2, shadow_color, thickness + 6, lineType=cv2.LINE_AA)
        cv2.circle(mask, (mid_x, mid_y), int(thickness * 1.3) + 3, shadow_color, -1)
        
        # Apply shadow by blending
        img_out = cv2.addWeighted(img_out, 1.0, mask, 0.15, 0)
        
        # Re-draw highlight on top
        cv2.circle(img_out, (mid_x, mid_y), int(thickness * 1.1), solder_color, -1)
        cv2.circle(img_out, (mid_x - thickness//4, mid_y - thickness//4), int(thickness * 0.4), highlight_color, -1)
        
        # Smooth boundaries
        img_out = cv2.GaussianBlur(img_out, (3, 3), 0)
        
        return img_out
