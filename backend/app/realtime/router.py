import asyncio
import json
import logging
import uuid

import jwt
from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..core.config import settings
from ..core.database import get_db
from ..core.redis import get_redis
from ..interview.models import InterviewSession
from ..interview.service import SessionService
from .connection import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()

def get_connection_manager(redis: Redis = Depends(get_redis)):
    return ConnectionManager(redis)

def get_session_service(db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)):
    return SessionService(db, redis)

async def verify_ws_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = str(payload.get("sub"))
        user_type = str(payload.get("type"))
        return {"id": user_id, "type": user_type}
    except Exception:
        raise ValueError("Invalid token")

from ..core.database import AsyncSessionLocal
@router.websocket("/sessions/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    manager: ConnectionManager = Depends(get_connection_manager),
    redis: Redis = Depends(get_redis)
):
    try:
        user = await verify_ws_token(token)
    except ValueError:
        print("WS ERROR: Invalid token"); await websocket.close(code=1008, reason="Invalid token")
        return
        
    user_id = user["id"]
    
    # Authorize session
    
    async with AsyncSessionLocal() as db:
        session_service = SessionService(db, redis)
        session_data = await session_service.get_session(session_id)

    if not session_data:
        print("WS ERROR: Session not found"); await websocket.close(code=1008, reason="Session not found")
        return
        
    is_participant = any(p["user_id"] == user_id for p in session_data["participants"])
    if not is_participant:
        print(f"WS ERROR: Forbidden for user {user_id} in session {session_data}"); await websocket.close(code=1008, reason="Forbidden")
        return
        
    # Check duplicate connections
    if user_id in manager.active_connections:
        # Close old connection
        old_ws = manager.active_connections[user_id]
        try:
            await old_ws.close(code=1000, reason="Duplicate connection")
        except Exception:
            pass

    await manager.connect(websocket, session_id, user_id)
    
    async def schedule_abandon(sess_id: str, u_id: str):
        # Grace period: 120s
        await asyncio.sleep(120)
        # Check presence
        presence_key = f"presence:{sess_id}:{u_id}"
        status = await redis.get(presence_key)
        if status == "DISCONNECTED":
            try:
                # Transition session to ABANDONED in PG
                if user["type"] == "REGISTERED":
                    # We need to lock and update
                    # For Phase 2A, we just update status and version
                    async with AsyncSessionLocal() as abandon_db:
                        res = await abandon_db.execute(
                            select(InterviewSession).where(InterviewSession.id == uuid.UUID(sess_id)).with_for_update()
                        )
                        sess_model = res.scalar_one_or_none()
                        if sess_model and sess_model.status != "COMPLETED" and sess_model.status != "ABANDONED":
                            sess_model.status = "ABANDONED"
                            sess_model.version += 1
                            await abandon_db.commit()
                else:
                    # Update Redis guest session
                    sess_key = f"guest_session:{sess_id}"
                    await redis.hset(sess_key, "status", "ABANDONED")
                    await redis.hincrby(sess_key, "version", 1)
                    
                # Broadcast ABANDONED event
                await manager.publish_event(sess_id, {
                    "type": "EVENT",
                    "event": "SESSION_ABANDONED",
                    "sessionId": sess_id,
                    "payload": {"reason": "DISCONNECT_TIMEOUT"}
                })
            except Exception as e:
                logger.error(f"Failed to abandon session {sess_id}: {e}")

    # Launch Redis subscriber
    sub_task = asyncio.create_task(manager.subscribe(session_id, websocket, user_id))
    
    try:
        while True:
            data = await websocket.receive_text()
            print("WS RECEIVED:", data)
            try:
                msg = json.loads(data)
                if msg.get("type") == "PING":
                    await websocket.send_json({"type": "PONG"})
                elif msg.get("type") == "COMMAND":
                    pass
                elif msg.get("type") == "CHAT_MESSAGE":
                    payload = msg.get("payload", {})
                    text = payload.get("text")
                    if text and isinstance(text, str) and len(text.strip()) > 0 and len(text) <= 500:
                        from datetime import datetime, UTC
                        # The server mints the authoritative message id so every
                        # client can dedupe its own echo and any reconnect replay.
                        chat_msg = {
                            "type": "CHAT_MESSAGE",
                            "payload": {
                                "id": str(uuid.uuid4()),
                                "sender_id": user_id,
                                "text": text.strip(),
                                "timestamp": datetime.now(UTC).isoformat()
                            }
                        }
                        await manager.publish_event(session_id, chat_msg)
                elif msg.get("type") == "IMAGE_SHARE":
                    payload = msg.get("payload", {})
                    data_uri = payload.get("image")
                    # Relayed exactly like chat — never written to Postgres or
                    # Redis, so there's nothing to clean up once the interview
                    # ends. ~2.7MB base64 (~2MB raw) caps a reasonably-sized
                    # photo without letting an arbitrarily large payload
                    # through the WS pipe and Redis pub/sub channel.
                    if (
                        isinstance(data_uri, str)
                        and data_uri.startswith("data:image/")
                        and len(data_uri) <= 2_800_000
                    ):
                        from datetime import UTC, datetime
                        image_msg = {
                            "type": "IMAGE_SHARE",
                            "payload": {
                                "id": str(uuid.uuid4()),
                                "sender_id": user_id,
                                "image": data_uri,
                                "timestamp": datetime.now(UTC).isoformat(),
                            }
                        }
                        await manager.publish_event(session_id, image_msg)
                elif msg.get("type") == "SIGNAL":
                    payload = msg.get("payload", {})
                    # Add sender identity safely to signal
                    signal_msg = {
                        "type": "SIGNAL",
                        "payload": {
                            "sender_id": user_id,
                            "signal": payload
                        }
                    }
                    await manager.publish_event(session_id, signal_msg)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        sub_task.cancel()
        await manager.disconnect(session_id, user_id, schedule_abandon=schedule_abandon)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        sub_task.cancel()
        await manager.disconnect(session_id, user_id, schedule_abandon=schedule_abandon)

