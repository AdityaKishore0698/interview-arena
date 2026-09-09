import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_guest(client: AsyncClient):
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    r1 = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    print("R1:", r1.json())
    r2 = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    print("R2:", r2.json())
