import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(String, index=True, nullable=False)  # Barcode / Serial Number of PCB
    status = Column(String, index=True, default="PENDING")  # PASS, FAIL, WARNING, PENDING_REVIEW
    image_url = Column(String, nullable=True)  # Path to MinIO storage
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Operator feedback
    operator_override = Column(Boolean, default=False)
    operator_verdict = Column(String, nullable=True)  # PASS, FAIL
    operator_notes = Column(Text, nullable=True)

    # Relationships
    defects = relationship("Defect", back_populates="inspection", cascade="all, delete-orphan")


class Defect(Base):
    __tablename__ = "defects"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    
    # Defect properties
    class_id = Column(Integer, nullable=False)
    class_name = Column(String, nullable=False)  # e.g., missing, misaligned, solder_bridge
    confidence = Column(Float, nullable=False)
    
    # Bounding Box Coordinates (normalized or absolute pixels)
    x_min = Column(Float, nullable=False)
    y_min = Column(Float, nullable=False)
    x_max = Column(Float, nullable=False)
    y_max = Column(Float, nullable=False)
    
    # Verification status (operator confirmation)
    status = Column(String, default="unconfirmed")  # unconfirmed, confirmed, false_positive
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    inspection = relationship("Inspection", back_populates="defects")
