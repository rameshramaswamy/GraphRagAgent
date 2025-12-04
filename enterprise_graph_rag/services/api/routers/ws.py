import asyncio
import json
import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from knowledge_engine.core.config import settings

router = APIRouter(tags=["Realtime"])

@router.websocket("/ws/status/{task_id}")
async def websocket_status(websocket: WebSocket, task_id: str):
    """
    Subscribes to updates for a specific task ID.
    """
    await websocket.accept()
    
    # Create Async Redis Connection
    r = redis.from_url(settings.REDIS_URL or "redis://localhost:6379/0")
    pubsub = r.pubsub()
    
    channel = f"task_updates:{task_id}"
    await pubsub.subscribe(channel)
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"].decode("utf-8")
                await websocket.send_text(data)
                
                # Close connection if completed
                parsed = json.loads(data)
                if parsed.get("status") in ["completed", "failed"]:
                    await websocket.close()
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await r.close()