"""A guest whose interview completes naturally (not via the Leave button)
must be able to queue up for a new one immediately, without logging out.
Regression test for a bug where a stale active_match/current_queue lock from
the finished session silently redirected the next join back to it — a
registered user's session already cleared these on completion; the guest
path didn't."""
import time

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis

from app.interview.lifecycle import advance_state

pytestmark = pytest.mark.asyncio


def _backdate(redis: Redis, session_key: str, field: str, seconds_ago: float = 999):
    """Rewrites a guest session's stored timestamp so the next advance_state
    tick sees its time window as already elapsed, instead of the test
    actually sleeping through QUICK mode's real (if short) durations."""
    return redis.hset(session_key, field, str(time.time() - seconds_ago))


async def _complete_a_guest_session(client: AsyncClient, redis: Redis, token_a: str, token_b: str, room_id: str) -> str:
    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    res_b = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    session_id = res_b.json()["match"]["match_id"]
    session_key = f"guest_session:{session_id}"

    await advance_state(session_id, is_guest=True)  # CREATED -> PREPARATION
    await _backdate(redis, session_key, "started_at")
    await advance_state(session_id, is_guest=True)  # PREPARATION -> ROUND_1_ACTIVE
    await _backdate(redis, session_key, "round_1_started_at")
    await advance_state(session_id, is_guest=True)  # ROUND_1_ACTIVE -> ROUND_1_FEEDBACK

    round1_id = "round_1_" + session_id
    for token in (token_a, token_b):
        res = await client.post(f"/api/v1/sessions/{session_id}/rounds/{round1_id}/feedback", json={"scores": {"overall": 4}}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
    await advance_state(session_id, is_guest=True)  # ROUND_1_FEEDBACK -> ROUND_2_ACTIVE (both_submitted)
    await _backdate(redis, session_key, "round_2_started_at")
    await advance_state(session_id, is_guest=True)  # ROUND_2_ACTIVE -> ROUND_2_FEEDBACK

    round2_id = "round_2_" + session_id
    for token in (token_a, token_b):
        res = await client.post(f"/api/v1/sessions/{session_id}/rounds/{round2_id}/feedback", json={"scores": {"overall": 4}}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
    active = await advance_state(session_id, is_guest=True)  # ROUND_2_FEEDBACK -> COMPLETED
    assert active is False

    status = await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert status.json()["status"] == "COMPLETED"
    return session_id


async def test_guest_can_requeue_immediately_after_a_completed_session(client: AsyncClient, redis: Redis):
    res_a = await client.post("/api/v1/auth/guest")
    token_a, guest_a = res_a.json()["access_token"], res_a.json()["guest_id"]
    res_b = await client.post("/api/v1/auth/guest")
    token_b, guest_b = res_b.json()["access_token"], res_b.json()["guest_id"]

    room_id = (await client.get("/api/v1/rooms/")).json()["rooms"][0]["id"]
    old_session_id = await _complete_a_guest_session(client, redis, token_a, token_b, room_id)

    # This is the actual bug: the stale lock from the finished session.
    assert await redis.get(f"active_match:{guest_a}") is None
    assert await redis.get(f"active_match:{guest_b}") is None
    assert await redis.get(f"current_queue:{guest_a}") is None
    assert await redis.get(f"current_queue:{guest_b}") is None

    rejoin = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_a}"})
    assert rejoin.json()["status"] != "ALREADY_MATCHED"

    rejoin_b = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "QUICK"}, headers={"Authorization": f"Bearer {token_b}"})
    new_session_id = rejoin_b.json()["match"]["match_id"]
    assert new_session_id != old_session_id

    fresh = await client.get(f"/api/v1/sessions/{new_session_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert fresh.json()["status"] in ("CREATED", "PREPARATION")  # a real new session, not the finished one
