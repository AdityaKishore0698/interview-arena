
import pytest
from httpx import AsyncClient

from app.core.redis import get_redis


@pytest.mark.asyncio
async def test_guest_lifecycle(client: AsyncClient):
    # 1. Create guest session
    response = await client.post("/api/v1/auth/guest")
    assert response.status_code == 201
    data = response.json()
    token = data["access_token"]
    guest_id = data["guest_id"]
    
    # 2. Verify TTL in Redis
    redis = await get_redis()
    ttl = await redis.ttl(f"session:{guest_id}")
    assert 0 < ttl <= 86400

    # 3. Retrieval / Validation (/me endpoint)
    me_response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json() == {"id": guest_id, "type": "GUEST"}

    # 4. Behavior after expiration
    await redis.delete(f"session:{guest_id}")  # Simulate expiration
    expired_response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert expired_response.status_code == 401
    assert expired_response.json()["detail"] == "Guest session expired"
