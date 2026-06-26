import os
import sys
import time
import subprocess
import logging
from fastapi.testclient import TestClient

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAsyncPipeline")

def run_async_integration_test():
    celery_worker_process = None
    worker_log = None
    try:
        # 1. Start Celery worker in a subprocess
        logger.info("Starting local Celery worker process for testing...")
        cmd = [
            ".venv/bin/celery",
            "-A", "backend.workers.celery_app.celery_app",
            "worker",
            "--loglevel=info",
            "--pool=solo"
        ]
        
        worker_log = open("celery_worker_async_test.log", "w")
        from backend.config import settings
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        for key, value in settings.model_dump().items():
            if value is not None:
                env[key] = str(value)
                
        celery_worker_process = subprocess.Popen(
            cmd,
            stdout=worker_log,
            stderr=worker_log,
            env=env,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None
        )
        
        # Give the worker a moment to start and connect to RabbitMQ
        logger.info("Waiting for worker to initialize...")
        time.sleep(3.0)

        # 2. Trigger inspection using FastAPI TestClient
        with TestClient(app) as client:
            board_id = "PCB-ASYNC-TEST-777"
            logger.info(f"Triggering async inspection for {board_id}...")
            payload = {"board_id": board_id}
            
            response = client.post("/api/inspections/trigger", json=payload)
            assert response.status_code == 201
            
            data = response.json()
            assert data["board_id"] == board_id
            assert data["status"] == "PENDING"
            inspection_id = data["id"]
            logger.info(f"Triggered inspection ID {inspection_id} successfully in PENDING state.")

            # 3. Poll database until status changes (timeout after 30s)
            start_time = time.time()
            max_wait = 30.0
            completed = False
            final_data = {}

            logger.info("Polling inspection status from API...")
            while time.time() - start_time < max_wait:
                time.sleep(1.0)
                status_resp = client.get(f"/api/inspections/{inspection_id}")
                assert status_resp.status_code == 200
                final_data = status_resp.json()
                current_status = final_data["status"]
                
                logger.info(f"Current inspection status: {current_status}")
                if current_status in ["PASS", "FAIL", "WARNING"]:
                    completed = True
                    break
                elif current_status == "ERROR":
                    logger.error("Worker set inspection status to ERROR.")
                    break
            
            assert completed, f"Async task timed out after {max_wait}s. Final status was {final_data.get('status')}"
            logger.info(f"Async task completed with status: {final_data['status']}.")
            
            # 4. Verify defects database insertion
            defects = final_data.get("defects", [])
            logger.info(f"Defects found: {len(defects)}")
            for d in defects:
                logger.info(f"Defect: Class={d['class_name']}, Conf={d['confidence']}, Box=[{d['x_min']},{d['y_min']},{d['x_max']},{d['y_max']}]")
                
            if final_data["status"] == "FAIL":
                assert len(defects) > 0, "Inspection failed but no defects were recorded in DB"
            elif final_data["status"] == "WARNING":
                logger.info(f"WARNING verdict — reason: {final_data.get('verdict_reason', 'N/A')}")
            else:
                logger.info(f"PASS verdict — severity: {final_data.get('severity', 'N/A')}")
                
            # 5. Clean up the test database entry
            logger.info(f"Cleaning up: deleting inspection ID {inspection_id}...")
            del_resp = client.delete(f"/api/inspections/{inspection_id}")
            assert del_resp.status_code == 204
            
            logger.info("Integration test PASSED successfully!")
            
    except Exception as e:
        logger.error(f"Integration test FAILED: {e}")
        sys.exit(1)
        
    finally:
        # 6. Safely terminate Celery worker
        if celery_worker_process:
            logger.info("Terminating local Celery worker...")
            celery_worker_process.terminate()
            try:
                celery_worker_process.wait(timeout=3.0)
                logger.info("Celery worker terminated.")
            except subprocess.TimeoutExpired:
                logger.warning("Celery worker did not terminate gracefully, killing it...")
                celery_worker_process.kill()
                logger.info("Celery worker killed.")
        if worker_log:
            worker_log.close()

if __name__ == "__main__":
    run_async_integration_test()
