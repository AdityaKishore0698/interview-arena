"""Guests get the same optional question-picking as registered users,
resolved from their Redis session instead of a database row (see
SessionService._select_problem_guest / _parse_guest_round_id)."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _matched_guest_pair(client: AsyncClient) -> dict:
    res_a = await client.post("/api/v1/auth/guest")
    token_a, id_a = res_a.json()["access_token"], res_a.json()["guest_id"]
    res_b = await client.post("/api/v1/auth/guest")
    token_b = res_b.json()["access_token"]

    rooms = (await client.get("/api/v1/rooms/")).json()["rooms"]
    room_id = next(r["id"] for r in rooms if r["slug"] == "dsa")

    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_a}"})
    res_join_b = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_b}"})
    session_id = res_join_b.json()["match"]["match_id"]

    session = (await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})).json()
    round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
    # Matchmaking assigns seat 1 (round 1's interviewer) to whichever join
    # actually triggers the match, not the one that joined first — same
    # lesson as the registered-users test, read the real assignment back
    # rather than assuming an order.
    interviewer_id = next(uid for uid, role in round1["roles"].items() if role == "INTERVIEWER")
    token_interviewer = token_a if interviewer_id == id_a else token_b
    token_interviewee = token_b if token_interviewer is token_a else token_a
    return {
        "token_interviewer": token_interviewer,
        "token_interviewee": token_interviewee,
        "session_id": session_id,
        "round_id": round1["id"],
        "room_id": room_id,
    }


async def test_guest_suggestions_and_selection_work(client: AsyncClient):
    ctx = await _matched_guest_pair(client)
    suggestions = (await client.get(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problems/suggestions",
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )).json()["problems"]
    assert len(suggestions) >= 1

    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem",
        json={"problem_id": suggestions[0]["id"]},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 200

    for token in (ctx["token_interviewer"], ctx["token_interviewee"]):
        session = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers={"Authorization": f"Bearer {token}"})).json()
        round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
        assert round1["problem"]["id"] == suggestions[0]["id"]
        assert round1["problem"]["custom"] is False


async def test_guest_custom_question_visible_to_both(client: AsyncClient):
    ctx = await _matched_guest_pair(client)
    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem",
        json={"custom_text": "Explain how you'd shard a key-value store."},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 200

    session = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers={"Authorization": f"Bearer {ctx['token_interviewee']}"})).json()
    round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
    assert round1["problem"]["custom"] is True
    assert round1["problem"]["prompt"] == "Explain how you'd shard a key-value store."


async def test_guest_non_interviewer_is_forbidden(client: AsyncClient):
    ctx = await _matched_guest_pair(client)
    headers = {"Authorization": f"Bearer {ctx['token_interviewee']}"}
    res = await client.get(f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problems/suggestions", headers=headers)
    assert res.status_code == 403
    res2 = await client.post(f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem", json={"custom_text": "x"}, headers=headers)
    assert res2.status_code == 403


async def test_guest_unknown_session_is_404(client: AsyncClient):
    guest = await client.post("/api/v1/auth/guest")
    token = guest.json()["access_token"]
    res = await client.get(
        "/api/v1/sessions/x/rounds/round_1_00000000-0000-0000-0000-000000000000/problems/suggestions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


async def test_guest_round_2_interviewer_is_the_other_user(client: AsyncClient):
    """Roles reverse for round 2 — user_b (round 1's interviewee) becomes
    round 2's interviewer, same convention as registered sessions."""
    ctx = await _matched_guest_pair(client)
    session = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers={"Authorization": f"Bearer {ctx['token_interviewer']}"})).json()
    round2 = next(r for r in session["rounds"] if r["round_number"] == 2)

    # Round 1's interviewer is now round 2's interviewee — forbidden there.
    forbidden = await client.get(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{round2['id']}/problems/suggestions",
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert forbidden.status_code == 403

    allowed = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{round2['id']}/problem",
        json={"custom_text": "Round 2 question from the reversed interviewer."},
        headers={"Authorization": f"Bearer {ctx['token_interviewee']}"},
    )
    assert allowed.status_code == 200

    refreshed = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers={"Authorization": f"Bearer {ctx['token_interviewer']}"})).json()
    round2_after = next(r for r in refreshed["rounds"] if r["round_number"] == 2)
    assert round2_after["problem"]["prompt"] == "Round 2 question from the reversed interviewer."
    # Round 1's own selection must be untouched by picking for round 2.
    round1_after = next(r for r in refreshed["rounds"] if r["round_number"] == 1)
    assert round1_after["problem"] is None


async def test_guest_picking_a_nonexistent_problem_is_rejected(client: AsyncClient):
    ctx = await _matched_guest_pair(client)
    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem",
        json={"problem_id": "00000000-0000-0000-0000-000000000000"},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 404
