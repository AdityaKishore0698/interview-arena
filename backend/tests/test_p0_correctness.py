import pytest
from httpx import AsyncClient
import uuid
from app.matchmaking.service import MatchmakingService
from app.core.redis import get_redis

@pytest.mark.asyncio
async def test_quick_cannot_match_standard(client: AsyncClient):
    # Setup users
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    # A joins QUICK
    res_join_a = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    assert res_join_a.json()["status"] == "QUEUED"
    
    # B joins STANDARD
    res_join_b = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_b}"})
    assert res_join_b.json()["status"] == "QUEUED"
    
    # They should NOT match
    status_a = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_a}"})
    assert status_a.json()["status"] == "QUEUED"

@pytest.mark.asyncio
async def test_guest_cannot_match_registered(client: AsyncClient):
    res_guest = await client.post("/api/v1/auth/guest")
    token_guest = res_guest.json()["access_token"]
    
    await client.post("/api/v1/auth/register", json={"email": "p0@ex.com", "password": "pass", "display_name": "P0"})
    res_reg = await client.post("/api/v1/auth/login", json={"email": "p0@ex.com", "password": "pass"})
    token_reg = res_reg.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_guest}"})
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_reg}"})
    
    status_guest = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_guest}"})
    assert status_guest.json()["status"] == "QUEUED"

@pytest.mark.asyncio
async def test_cannot_join_queue_if_active_match(client: AsyncClient):
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    res_match = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    assert res_match.json()["status"] == "MATCH_FOUND"
    
    # User B tries to join STANDARD now
    res_rejoin = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_b}"})
    # Should be rejected or returned as ALREADY_MATCHED
    assert res_rejoin.json()["status"] == "ALREADY_MATCHED"
