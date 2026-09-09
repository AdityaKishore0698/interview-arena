import pytest
from httpx import AsyncClient
from app.core.redis import get_redis
from app.core.database import get_db
import asyncio

@pytest.mark.asyncio
async def test_12_session_integrity(client: AsyncClient):
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    await asyncio.sleep(0.5)
    
    status_a = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_a}"})
    match_id = status_a.json()["match_id"]
    
    session_res = await client.get(f"/api/v1/sessions/{match_id}", headers={"Authorization": f"Bearer {token_a}"})
    sess = session_res.json()
    
    assert len(sess["participants"]) == 2, "Exactly two participants required"
    assert sess["room_id"] == room_id
    
