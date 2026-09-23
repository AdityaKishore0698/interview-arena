"""Guests get the same optional code editor as registered users, mirrored
into their Redis session instead of a database row (see
SessionService.submit_code / _require_guest_interviewee)."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _matched_guest_pair(client: AsyncClient, problem_title: str | None = None) -> dict:
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
    interviewer_id = next(uid for uid, role in round1["roles"].items() if role == "INTERVIEWER")
    token_interviewer = token_a if interviewer_id == id_a else token_b
    token_interviewee = token_b if token_interviewer is token_a else token_a

    if problem_title:
        suggestions = (await client.get(
            f"/api/v1/sessions/{session_id}/rounds/{round1['id']}/problems/suggestions",
            headers={"Authorization": f"Bearer {token_interviewer}"},
        )).json()["problems"]
        chosen = next(p for p in suggestions if p["title"] == problem_title)
        await client.post(
            f"/api/v1/sessions/{session_id}/rounds/{round1['id']}/problem",
            json={"problem_id": chosen["id"]},
            headers={"Authorization": f"Bearer {token_interviewer}"},
        )

    return {
        "token_interviewer": token_interviewer,
        "token_interviewee": token_interviewee,
        "session_id": session_id,
        "round_id": round1["id"],
    }


async def test_guest_only_interviewee_can_submit_code(client: AsyncClient):
    ctx = await _matched_guest_pair(client, problem_title="Two Sum")
    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/submit",
        json={"language": "python", "code": "print('hi')"},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 403


async def test_guest_code_submission_persists_and_is_visible_to_both(client: AsyncClient):
    ctx = await _matched_guest_pair(client, problem_title="Two Sum")
    code = "print('0 1')"

    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/submit",
        json={"language": "javascript", "code": code},
        headers={"Authorization": f"Bearer {ctx['token_interviewee']}"},
    )
    assert res.status_code == 200

    for token in (ctx["token_interviewer"], ctx["token_interviewee"]):
        session = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers={"Authorization": f"Bearer {token}"})).json()
        round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
        assert round1["submitted_code"] == code
        assert round1["submitted_language"] == "javascript"
