
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_get_session_guest(client: AsyncClient):
    # Setup users
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    user_a = res_a.json()["guest_id"]
    
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    res2 = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    
    match = res2.json()["match"]
    session_id = match["match_id"]
    
    # Authoritative Snapshot
    res_sync = await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_sync.status_code == 200
    data = res_sync.json()
    assert data["id"] == session_id
    assert data["version"] in [1, 2]
    
    # Try fetching with someone else
    res_c = await client.post("/api/v1/auth/guest")
    token_c = res_c.json()["access_token"]
    res_fail = await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_c}"})
    assert res_fail.status_code == 403

async def test_get_session_registered(client: AsyncClient):
    # Register A
    await client.post("/api/v1/auth/register", json={"email": "m10@example.com", "password": "pass", "display_name": "M10"})
    res_a = await client.post("/api/v1/auth/login", json={"email": "m10@example.com", "password": "pass"})
    token_a = res_a.json()["access_token"]
    
    # Register B
    await client.post("/api/v1/auth/register", json={"email": "m11@example.com", "password": "pass", "display_name": "M11"})
    res_b = await client.post("/api/v1/auth/login", json={"email": "m11@example.com", "password": "pass"})
    token_b = res_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    res2 = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    
    match = res2.json()["match"]
    session_id = match["match_id"]
    
    res_sync = await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_sync.status_code == 200
    assert res_sync.json()["version"] == 1
