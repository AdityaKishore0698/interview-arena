import asyncio
import json
import logging
from collections.abc import Callable

from fastapi import WebSocket
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self, redis: Redis):
        self.redis = redis
        # map user_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        # Track presence in Redis
        presence_key = f"presence:{session_id}:{user_id}"
        await self.redis.set(presence_key, "CONNECTED", ex=86400) # 24h
        
        # Check for already connected participants
        keys = await self.redis.keys(f"presence:{session_id}:*")
        for k in keys:
            if k != presence_key:
                val = await self.redis.get(k)
                if val and val == "CONNECTED":
                    opp_id = k.split(":")[-1]
                    await websocket.send_text(json.dumps({
                        "type": "EVENT",
                        "event": "OPPONENT_CONNECTED",
                        "sessionId": session_id,
                        "payload": {"userId": opp_id}
                    }))
        
        # Publish connect event
        await self.publish_event(session_id, {
            "type": "EVENT",
            "event": "OPPONENT_CONNECTED",
            "sessionId": session_id,
            "payload": {"userId": user_id}
        })

    async def disconnect(self, session_id: str, user_id: str, schedule_abandon: Callable | None = None):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            
        presence_key = f"presence:{session_id}:{user_id}"
        await self.redis.set(presence_key, "DISCONNECTED", ex=86400)
        
        # Publish disconnect event
        await self.publish_event(session_id, {
            "type": "EVENT",
            "event": "OPPONENT_DISCONNECTED",
            "sessionId": session_id,
            "payload": {"userId": user_id}
        })
        
        if schedule_abandon:
            asyncio.create_task(schedule_abandon(session_id, user_id))

    async def publish_event(self, session_id: str, event_data: dict):
        channel = f"session:{session_id}:events"
        print("Publishing:", channel, event_data)
        await self.redis.publish(channel, json.dumps(event_data))
        
    async def subscribe(self, session_id: str, websocket: WebSocket, user_id: str = ""):
        pubsub = self.redis.pubsub()
        channel = f"session:{session_id}:events"
        await pubsub.subscribe(channel)
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                print("PubSub message:", message)
                if message and message.get("type") == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    
                    try:
                        msg_obj = json.loads(data)
                        if msg_obj.get("event") in ("OPPONENT_CONNECTED", "OPPONENT_DISCONNECTED"):
                            if msg_obj.get("payload", {}).get("userId") == user_id:
                                continue
                    except Exception:
                        pass

                    await websocket.send_text(data)
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"PubSub error for session {session_id}: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            
