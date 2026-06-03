"""WebSocket alert streaming — spec section 11 + 13."""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(tags=["websocket"])

# Connection manager
class AlertConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = AlertConnectionManager()


@router.websocket("/alerts/live")
async def websocket_alerts(
    websocket: WebSocket,
    token: str = Query(None),
):
    """
    Real-time event stream — spec section 11.
    Streams all events >= L2 via WebSocket.
    Browser Push Notification data included for L3 events.
    """
    # Authenticate via token query param
    if token:
        try:
            payload = jwt.decode(token, settings.secret_key,
                                  algorithms=[settings.jwt_algorithm])
        except JWTError:
            await websocket.close(code=4001)
            return
    else:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket)
    try:
        # Subscribe to Redis pub/sub
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe("alerts")

            async def redis_listener():
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        try:
                            data = json.loads(msg["data"])
                            severity = data.get("severity", "L1")
                            # Spec: WebSocket for >= L2
                            if severity in ("L2", "L2+", "L3"):
                                payload_out = {
                                    "type": "alert",
                                    "event": data,
                                    # Spec: browser push for L3
                                    "push_notification": severity == "L3",
                                }
                                await manager.broadcast(payload_out)
                        except Exception:
                            pass

            listener_task = asyncio.create_task(redis_listener())

            # Keep connection alive
            while True:
                try:
                    msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                    if msg == "ping":
                        await websocket.send_json({"type": "pong"})
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "heartbeat"})
                except WebSocketDisconnect:
                    break

            listener_task.cancel()
            await pubsub.unsubscribe("alerts")
            await r.aclose()

        except Exception:
            # Redis unavailable — keep connection open for manual pushes
            while True:
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=30)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "heartbeat"})
                except WebSocketDisconnect:
                    break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


async def push_alert(event: dict):
    """Called by processing pipeline to push events to connected clients."""
    if event.get("severity") in ("L2", "L2+", "L3"):
        await manager.broadcast({
            "type": "alert",
            "event": event,
            "push_notification": event.get("severity") == "L3",
        })
