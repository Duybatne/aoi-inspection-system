import os
import glob
import logging
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import cv2
import torch
from torch.utils.data import Dataset

logger = logging.getLogger("DatasetBuilder")

class PCBDefectDataset(Dataset):
    """
    Custom PyTorch Dataset for PCB Defect Detection supporting YOLO annotation format.
    Annotations are expected to be in standard YOLO text files:
    <class_id> <x_center> <y_center> <width> <height> (all normalized 0.0 to 1.0)
    """
    def __init__(
        self,
        img_dir: str,
        label_dir: str,
        transform: Optional[Any] = None,
        class_mapping: Optional[Dict[int, str]] = None
    ):
        self.img_dir = img_dir
        self.label_dir = label_dir
        self.transform = transform
        
        # Default DeepPCB / standard 6 classes if not provided
        self.class_mapping = class_mapping or {
            0: "open",
            1: "short",
            2: "mousebite",
            3: "spur",
            4: "spurious_copper",
            5: "pin_hole"
        }
        
        self.image_paths = sorted(
            glob.glob(os.path.join(img_dir, "*.jpg")) + 
            glob.glob(os.path.join(img_dir, "*.png"))
        )
        logger.info(f"Loaded {len(self.image_paths)} images from {img_dir}")

    def __len__(self) -> int:
        return len(self.image_paths)

    def _load_yolo_labels(self, label_path: str) -> List[List[float]]:
        """Reads YOLO format label file and returns a list of [class_id, x, y, w, h]"""
        labels = []
        if not os.path.exists(label_path):
            return labels
            
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 5:
                    class_id = int(parts[0])
                    coords = [float(x) for x in parts[1:]]
                    labels.append([class_id] + coords)
        return labels

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, Any]]:
        img_path = self.image_paths[idx]
        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, _ = image.shape
        
        # Determine label path corresponding to the image filename
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(self.label_dir, f"{base_name}.txt")
        
        raw_labels = self._load_yolo_labels(label_path)
        
        bboxes = []
        class_ids = []
        for lbl in raw_labels:
            class_id, x_c, y_c, bw, bh = lbl
            # Convert normalized YOLO format to absolute pixels (or albumentations standard format)
            # YOLO format: normalized x_center, y_center, width, height
            # Albumentations format: normalized x_min, y_min, x_max, y_max or pascal_voc
            bboxes.append([x_c, y_c, bw, bh])
            class_ids.append(class_id)

        # Apply transformations using Albumentations
        if self.transform:
            # Albumentations needs bboxes in [x_min, y_min, x_max, y_max] normalized or similar format
            # We'll use yolo format directly since Albumentations supports 'yolo' bbox format
            transformed = self.transform(
                image=image,
                bboxes=bboxes,
                class_labels=class_ids
            )
            image = transformed['image']
            bboxes = transformed['bboxes']
            class_ids = transformed['class_labels']

        # Convert image to PyTorch tensor format (C, H, W)
        image_tensor = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        
        target = {
            "bboxes": torch.tensor(bboxes, dtype=torch.float32),
            "labels": torch.tensor(class_ids, dtype=torch.int64),
            "image_path": img_path,
            "orig_size": (h, w)
        }
        
        return image_tensor, target
