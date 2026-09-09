import pytest
from httpx import AsyncClient

from app.interview.lifecycle import advance_state


@pytest.mark.asyncio
async def test_feedback_idempotency(client: AsyncClient):
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
    # Tick 2: PREPARATION -> ROUND 1
    await advance_state(session_id, is_guest=True)
    # Tick 3: ROUND 1 -> FEEDBACK
    await advance_state(session_id, is_guest=True)
    
    sess_res = await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})
    round_id = sess_res.json()["rounds"][0]["id"] if sess_res.json().get("rounds") else "1"
    
    # Submit feedback 1st time
    res = await client.post(f"/api/v1/sessions/{session_id}/rounds/{round_id}/feedback", json={"scores": {"overall": 5}, "comments": "Good"}, headers={"Authorization": f"Bearer {token_a}"})
    print(res.json())
    assert res.status_code == 200
    
    # Submit feedback 2nd time
    res = await client.post(f"/api/v1/sessions/{session_id}/rounds/{round_id}/feedback", json={"scores": {"overall": 5}, "comments": "Good again"}, headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 409
