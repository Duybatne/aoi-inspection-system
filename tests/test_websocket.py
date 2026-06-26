import os
import sys
import time
import json
import subprocess
import logging
from fastapi.testclient import TestClient

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestWebSocket")

def run_websocket_integration_test():
    celery_worker_process = None
    worker_log = None
    try:
        # 1. Start local Celery worker
        logger.info("Starting local Celery worker for WebSocket testing...")
        cmd = [
            ".venv/bin/celery",
            "-A", "backend.workers.celery_app.celery_app",
            "worker",
            "--loglevel=info",
            "--pool=solo"
        ]
        
        # Open log file to avoid pipe buffer deadlock
        worker_log = open("celery_worker_ws_test.log", "w")
        
        # Propagate config settings to environment variables for subprocess
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
        
        # Give the worker a moment to connect to RabbitMQ and Redis
        logger.info("Waiting for worker initialization...")
        time.sleep(3.0)

        # 2. Run TestClient connection context
        with TestClient(app) as client:
            # Connect to WebSocket
            logger.info("Connecting to WebSocket /ws...")
            with client.websocket_connect("/ws") as websocket:
                # Trigger a scan via REST
                board_id = "WS-TEST-BOARD-888"
                logger.info(f"Triggering scan for {board_id}...")
                response = client.post("/api/inspections/trigger", json={"board_id": board_id})
                assert response.status_code == 201
                
                trigger_data = response.json()
                inspection_id = trigger_data["id"]
                logger.info(f"Triggered inspection ID {inspection_id}. Monitoring WebSocket for events...")

                # Receive events
                events_received = []
                
                # We expect 2 events: processing and completed
                # Allow a max wait of 25s
                start_time = time.time()
                while len(events_received) < 2 and (time.time() - start_time < 25.0):
                    try:
                        # Wait for a message with timeout
                        msg_str = websocket.receive_text()
                        msg = json.loads(msg_str)
                        logger.info(f"Received WS Event: {msg.get('event')}")
                        events_received.append(msg)
                    except Exception as ws_err:
                        logger.warning(f"Error receiving WS message: {ws_err}")
                        time.sleep(0.5)

                assert len(events_received) >= 2, f"Expected 2 events, got {len(events_received)}"
                
                # Assert first event is inspection_processing
                assert events_received[0]["event"] == "inspection_processing"
                assert events_received[0]["data"]["id"] == inspection_id
                assert events_received[0]["data"]["status"] == "PROCESSING"
                
                # Assert second event is inspection_completed
                assert events_received[1]["event"] == "inspection_completed"
                assert events_received[1]["data"]["id"] == inspection_id
                assert events_received[1]["data"]["status"] in ["PASS", "FAIL"]
                
                logger.info("All real-time events verified successfully!")

                # Cleanup test inspection from DB
                logger.info(f"Cleaning up: deleting inspection ID {inspection_id}...")
                del_resp = client.delete(f"/api/inspections/{inspection_id}")
                assert del_resp.status_code == 204
                
                logger.info("WebSocket Integration Test PASSED successfully!")
                
    except Exception as e:
        logger.error(f"WebSocket Integration Test FAILED: {e}")
        sys.exit(1)
        
    finally:
        # 3. Clean up Celery worker
        if celery_worker_process:
            logger.info("Terminating local Celery worker...")
            celery_worker_process.terminate()
            try:
                celery_worker_process.wait(timeout=3.0)
                logger.info("Celery worker terminated.")
            except subprocess.TimeoutExpired:
                celery_worker_process.kill()
                logger.info("Celery worker killed.")
        if worker_log:
            worker_log.close()

if __name__ == "__main__":
    run_websocket_integration_test()
