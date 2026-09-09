import pytest
from httpx import AsyncClient
from app.core.redis import get_redis
import asyncio
import json

@pytest.mark.asyncio
async def test_1_guest_quick_vs_quick(client: AsyncClient):
    redis = await get_redis()
    
    # 1. Setup Guests
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    user_a_id = res_a.json()["guest_id"]
    
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    user_b_id = res_b.json()["guest_id"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    # 2. Join Queue
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    
    # Give matchmaking task a moment
    await asyncio.sleep(0.5)
    
    # 3. Status checks
    status_a = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_a}"})
    status_b = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_b}"})
    
    assert status_a.json()["status"] == "MATCH_FOUND"
    assert status_b.json()["status"] == "MATCH_FOUND"
    
    match_id_a = status_a.json()["match_id"]
    match_id_b = status_b.json()["match_id"]
    assert match_id_a == match_id_b, "Both must see same session_id"
    
    # 4. Fetch Session Hydration
    session_res_a = await client.get(f"/api/v1/sessions/{match_id_a}", headers={"Authorization": f"Bearer {token_a}"})
    sess_a = session_res_a.json()
    assert sess_a["status"] == "PREPARATION"
    assert len(sess_a["participants"]) == 2
    assert "rounds" in sess_a
    
    # Ensure no 'observer', exactly one INTERVIEWER and one INTERVIEWEE
    r1_roles = sess_a["rounds"][0]["roles"]
    assert len(r1_roles) == 2
    roles_list = list(r1_roles.values())
    assert "INTERVIEWER" in roles_list and "INTERVIEWEE" in roles_list
    
    # Round 2 reversed
    r2_roles = sess_a["rounds"][1]["roles"]
    assert r1_roles[user_a_id] != r2_roles[user_a_id], "Roles must reverse"

@pytest.mark.asyncio
async def test_2_guest_quick_vs_standard(client: AsyncClient):
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_b}"})
    
    await asyncio.sleep(0.5)
    status_a = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_a}"})
    status_b = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_b}"})
    
    assert status_a.json()["status"] == "QUEUED"
    assert status_b.json()["status"] == "QUEUED"

@pytest.mark.asyncio
async def test_3_guest_quick_no_opponent(client: AsyncClient):
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    
    await asyncio.sleep(0.5)
    status_a = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_a}"})
    
    assert status_a.json()["status"] == "QUEUED"
    assert "match_id" not in status_a.json()

@pytest.mark.asyncio
async def test_4_session_completion_cleanup(client: AsyncClient):
    redis = await get_redis()
    
    # 1. Setup Guests
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    user_a_id = res_a.json()["guest_id"]
    
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    user_b_id = res_b.json()["guest_id"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    # 2. Join & Match
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    await asyncio.sleep(0.5)
    
    status = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_a}"})
    match_id = status.json()["match_id"]
    
    # Ensure keys exist
    assert await redis.exists(f"active_match:{user_a_id}")
    assert await redis.exists(f"active_match:{user_b_id}")
    
    # 3. Terminate session (leave)
    await client.post(f"/api/v1/sessions/{match_id}/leave", headers={"Authorization": f"Bearer {token_a}"})
    
    # Wait for lifecycle to clear it
    await asyncio.sleep(0.2)
    
    # 4. Verify cleanup
    assert not await redis.exists(f"active_match:{user_a_id}"), "active_match A should be deleted"
    assert not await redis.exists(f"active_match:{user_b_id}"), "active_match B should be deleted"
    assert not await redis.exists(f"current_queue:{user_a_id}"), "current_queue A should be deleted"
    assert not await redis.exists(f"current_queue:{user_b_id}"), "current_queue B should be deleted"
    
    # 5. A joins again
    res_join = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    assert res_join.json()["status"] == "QUEUED"
    
    status_a = await client.get("/api/v1/matchmaking/status", headers={"Authorization": f"Bearer {token_a}"})
    assert status_a.json()["status"] == "QUEUED", "A must remain SEARCHING, no stale match"

