import logging
from typing import Tuple
import albumentations as A
from albumentations.pytorch import ToTensorV2

logger = logging.getLogger("AugmentationPipeline")

def get_train_transforms(img_size: Tuple[int, int] = (640, 640)) -> A.Compose:
    """
    Returns training augmentation pipeline with bounding box support.
    Accepts YOLO format bounding boxes.
    """
    logger.info("Initializing training augmentation pipeline...")
    return A.Compose(
        [
            A.Resize(height=img_size[1], width=img_size[0]),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.RandomRotate90(p=0.5),
            A.ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.1, rotate_limit=15, p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.3),
        ],
        bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels'],
            min_visibility=0.3
        )
    )

def get_val_transforms(img_size: Tuple[int, int] = (640, 640)) -> A.Compose:
    """
    Returns validation/inference validation pipeline.
    """
    logger.info("Initializing validation augmentation pipeline...")
    return A.Compose(
        [
            A.Resize(height=img_size[1], width=img_size[0]),
        ],
        bbox_params=A.BboxParams(
            format='yolo',
            label_fields=['class_labels'],
            min_visibility=0.3
        )
    )
