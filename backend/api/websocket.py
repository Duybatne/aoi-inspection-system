import json
import logging
import asyncio
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import asyncio as aioredis
from backend.config import settings

logger = logging.getLogger("WebSocketManager")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")

manager = ConnectionManager()
ws_router = APIRouter()

@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Create a dedicated Redis connection for this WebSocket client
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("aoi_events")
    logger.info("WebSocket client subscribed to Redis channel 'aoi_events'")
    
    try:
        # Keep client connection alive and listen for incoming client messages in the background
        async def client_receiver():
            try:
                while True:
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_text("pong")
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error in client_receiver: {e}")

        # Listen to Redis Pub/Sub and stream events to the client
        async def redis_listener():
            try:
                async for message in pubsub.listen():
                    if message and message["type"] == "message":
                        try:
                            # Send message as text directly to this client
                            await websocket.send_text(message["data"])
                        except Exception as send_err:
                            logger.error(f"Failed to send data to WebSocket client: {send_err}")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in redis_listener: {e}")

        # Run both tasks concurrently
        await asyncio.gather(client_receiver(), redis_listener())
        
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally.")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        manager.disconnect(websocket)
        try:
            await pubsub.unsubscribe("aoi_events")
            await redis_client.close()
        except Exception as close_err:
            logger.error(f"Error closing Redis pubsub on WS disconnect: {close_err}")
