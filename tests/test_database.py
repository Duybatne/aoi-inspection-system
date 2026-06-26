import os
import sys
import logging

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, SessionLocal
from backend.models.database import Inspection, Defect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestDatabase")

def main():
    logger.info("Initializing database tables...")
    init_db()
    
    db = SessionLocal()
    try:
        logger.info("Creating a new test inspection...")
        new_inspection = Inspection(
            board_id="PCB-TEST-12345",
            status="FAIL",
            image_url="http://localhost:9000/aoi-pcb-images/PCB-TEST-12345.png"
        )
        db.add(new_inspection)
        db.commit()
        db.refresh(new_inspection)
        
        logger.info(f"Created inspection ID: {new_inspection.id}")
        
        logger.info("Adding defects to inspection...")
        defect1 = Defect(
            inspection_id=new_inspection.id,
            class_id=0,
            class_name="missing",
            confidence=0.89,
            x_min=120.0,
            y_min=240.0,
            x_max=220.0,
            y_max=300.0
        )
        defect2 = Defect(
            inspection_id=new_inspection.id,
            class_id=2,
            class_name="solder_bridge",
            confidence=0.95,
            x_min=500.0,
            y_min=620.0,
            x_max=600.0,
            y_max=700.0
        )
        
        db.add_all([defect1, defect2])
        db.commit()
        
        # Verify
        logger.info("Querying database to verify inspection and defects...")
        queried_inspection = db.query(Inspection).filter(Inspection.id == new_inspection.id).first()
        assert queried_inspection is not None
        assert len(queried_inspection.defects) == 2
        
        logger.info(f"Verified inspection {queried_inspection.board_id} with {len(queried_inspection.defects)} defects.")
        for d in queried_inspection.defects:
            logger.info(f"  - Defect: {d.class_name} with confidence {d.confidence}")
            
        # Clean up
        logger.info("Cleaning up test data...")
        db.delete(queried_inspection)
        db.commit()
        
        logger.info("Database tests passed successfully!")
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
