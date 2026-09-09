import uuid

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.redis import get_redis


@pytest.mark.asyncio
async def test_rooms_api(client: AsyncClient):
    response = await client.get("/api/v1/rooms/")
    assert response.status_code == 200
    data = response.json()
    assert "rooms" in data
    assert len(data["rooms"]) >= 3
    slugs = [r["slug"] for r in data["rooms"]]
    assert "dsa" in slugs
    assert "system-design" in slugs

@pytest.mark.asyncio
async def test_guest_auth(client: AsyncClient):
    response = await client.post("/api/v1/auth/guest")
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "guest_id" in data
    assert data["token_type"] == "bearer"
    
    # Verify Redis session
    redis = await get_redis()
    session = await redis.get(f"session:{data['guest_id']}")
    assert session is not None
    assert '"type": "GUEST"' in session

    # Verify JWT
    decoded = jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == data["guest_id"]
    assert decoded["type"] == "GUEST"

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    unique_email = f"test_{uuid.uuid4()}@example.com"
    
    # 1. Register
    reg_response = await client.post("/api/v1/auth/register", json={
        "email": unique_email,
        "password": "securepassword",
        "display_name": "Test User"
    })
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert "user_id" in reg_data

    # 2. Register again (conflict)
    reg_conflict = await client.post("/api/v1/auth/register", json={
        "email": unique_email,
        "password": "securepassword",
        "display_name": "Test User 2"
    })
    assert reg_conflict.status_code == 409

    # 3. Login
    login_response = await client.post("/api/v1/auth/login", json={
        "email": unique_email,
        "password": "securepassword"
    })
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    
    # 4. Login Invalid
    login_invalid = await client.post("/api/v1/auth/login", json={
        "email": unique_email,
        "password": "wrongpassword"
    })
    assert login_invalid.status_code == 401
