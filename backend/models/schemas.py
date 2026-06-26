from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DefectBase(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    status: str

class DefectResponse(DefectBase):
    id: int
    inspection_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class InspectionBase(BaseModel):
    board_id: str
    status: str
    image_url: Optional[str] = None
    operator_override: bool = False
    operator_verdict: Optional[str] = None
    operator_notes: Optional[str] = None

class InspectionCreate(BaseModel):
    board_id: str

class InspectionResponse(InspectionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    defects: List[DefectResponse] = []

    class Config:
        from_attributes = True

class OverrideRequest(BaseModel):
    operator_verdict: str  # PASS or FAIL
    operator_notes: Optional[str] = None
