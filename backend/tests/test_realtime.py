import uuid

import pytest

from app.realtime.connection import ConnectionManager
from app.realtime.router import verify_ws_token

pytestmark = pytest.mark.asyncio

async def test_verify_ws_token(client):
    # Get real token
    res = await client.post("/api/v1/auth/guest")
    token = res.json()["access_token"]
    
    user = await verify_ws_token(token)
    assert user["type"] == "GUEST"
    
    with pytest.raises(ValueError):
        await verify_ws_token("invalid")

async def test_connection_manager_connect_disconnect(redis):
    manager = ConnectionManager(redis)
    session_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    class MockWebSocket:
        async def accept(self): pass
        async def send_text(self, data): pass
        async def close(self, code, reason): pass
        
    ws = MockWebSocket()
    
    # Test connect
    await manager.connect(ws, session_id, user_id)
    assert user_id in manager.active_connections
    
    presence = await redis.get(f"presence:{session_id}:{user_id}")
    assert presence == "CONNECTED"
    
    # Test disconnect
    await manager.disconnect(session_id, user_id)
    assert user_id not in manager.active_connections
    
    presence = await redis.get(f"presence:{session_id}:{user_id}")
    assert presence == "DISCONNECTED"
    
