import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.redis import get_redis
from app.interview.models import InterviewSession

pytestmark = pytest.mark.asyncio

async def test_join_queue_no_match(client: AsyncClient):
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    
    res = await client.post("/api/v1/matchmaking/join", json={
        "room_id": str(uuid.uuid4()),
        "mode": "QUICK"
    }, headers={"Authorization": f"Bearer {token_a}"})
    
    assert res.status_code == 200
    assert res.json()["status"] == "QUEUED"

async def test_join_queue_match_found(client: AsyncClient, db_session: AsyncSession):
    # Setup users
    await client.post("/api/v1/auth/register", json={
        "email": "m2@example.com", "password": "pass", "display_name": "M2"
    })
    res_login_a = await client.post("/api/v1/auth/login", json={"email": "m2@example.com", "password": "pass"})
    assert res_login_a.status_code == 200, res_login_a.text
    token_a = res_login_a.json()["access_token"]
    
    await client.post("/api/v1/auth/register", json={
        "email": "m3@example.com", "password": "pass", "display_name": "M3"
    })
    res_login_b = await client.post("/api/v1/auth/login", json={"email": "m3@example.com", "password": "pass"})
    assert res_login_b.status_code == 200, res_login_b.text
    token_b = res_login_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    res1 = await client.post("/api/v1/matchmaking/join", json={
        "room_id": room_id, "mode": "QUICK"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert res1.json()["status"] == "QUEUED"
    
    res2 = await client.post("/api/v1/matchmaking/join", json={
        "room_id": room_id, "mode": "QUICK"
    }, headers={"Authorization": f"Bearer {token_b}"})
    
    data = res2.json()
    assert data["status"] == "MATCH_FOUND"
    match = data["match"]
    assert match["status"] == "NEW_MATCH"
    
    result = await db_session.execute(select(InterviewSession).where(InterviewSession.id == uuid.UUID(match["match_id"])))
    session = result.scalar_one_or_none()
    assert session is not None
    assert session.mode == "QUICK"
    
    redis = await get_redis()
    queue_key = f"queue:{room_id}:QUICK:REGISTERED"
    count = await redis.zcard(queue_key)
    assert count == 0

async def test_leave_queue(client: AsyncClient):
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    
    room_id = str(uuid.uuid4())
    
    await client.post("/api/v1/matchmaking/join", json={
        "room_id": room_id, "mode": "QUICK"
    }, headers={"Authorization": f"Bearer {token_a}"})
    
    res = await client.post("/api/v1/matchmaking/leave", json={
        "room_id": room_id, "mode": "QUICK"
    }, headers={"Authorization": f"Bearer {token_a}"})
    
    assert res.json()["status"] == "CANCELED"
    
    redis = await get_redis()
    queue_key = f"queue:{room_id}:QUICK:GUEST"
    count = await redis.zcard(queue_key)
    assert count == 0
