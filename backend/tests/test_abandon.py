
import pytest
from httpx import AsyncClient

from app.interview.lifecycle import advance_state


@pytest.mark.asyncio
async def test_early_abandonment(client: AsyncClient):
    # Setup registered users
    res_a = await client.post("/api/v1/auth/guest")
    token_a = res_a.json()["access_token"]
    
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]
    
    res_rooms = await client.get("/api/v1/rooms/")
    room_id = res_rooms.json()["rooms"][0]["id"]
    
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    res2 = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    
    session_id = res2.json()["match"]["match_id"]
    
    # Tick 1: CREATED -> PREPARATION
    await advance_state(session_id, is_guest=True)
    
    # User A leaves
    leave_res = await client.post(f"/api/v1/sessions/{session_id}/leave", headers={"Authorization": f"Bearer {token_a}"})
    assert leave_res.status_code == 200
    
    sess_res = await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})
    print(sess_res.json())
    assert sess_res.json().get("status") == "ABANDONED"
