"""The interviewer for a round may optionally pick its question — from the
suggested bank, or a free-form one of their own — and the choice is visible
to both participants immediately, even before the round starts. Not picking
at all leaves the existing deterministic auto-pick-once-started behavior
unchanged (test_p0_matrix_5_12 / test_integration already cover that path)."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.interview.models import InterviewRound

pytestmark = pytest.mark.asyncio


async def _matched_pair(client: AsyncClient) -> dict:
    """Registers two users and matches them. Which one lands on seat 1 (and
    so is round 1's INTERVIEWER) isn't the join order — MatchmakingService
    assigns seat 1 to whichever call actually triggers the match, not the
    one that was already waiting — so this reads the round's `roles` map
    back from the API rather than assuming an order."""
    suffix = uuid.uuid4().hex[:10]
    email_a, email_b = f"picker_a_{suffix}@example.com", f"picker_b_{suffix}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email_a, "password": "pass", "display_name": "A"})
    await client.post("/api/v1/auth/register", json={"email": email_b, "password": "pass", "display_name": "B"})
    token_a = (await client.post("/api/v1/auth/login", json={"email": email_a, "password": "pass"})).json()["access_token"]
    token_b = (await client.post("/api/v1/auth/login", json={"email": email_b, "password": "pass"})).json()["access_token"]
    id_a = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})).json()["id"]

    rooms = (await client.get("/api/v1/rooms/")).json()["rooms"]
    room_id = next(r["id"] for r in rooms if r["slug"] == "dsa")

    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_a}"})
    res_b = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_b}"})
    match = res_b.json()["match"]
    session_id = match["match_id"]
    assert match["user_a"] != match["user_b"]

    session = (await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})).json()
    round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
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


async def test_suggestions_list_matches_room_and_slot(client: AsyncClient):
    ctx = await _matched_pair(client)
    res = await client.get(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problems/suggestions",
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 200
    problems = res.json()["problems"]
    assert len(problems) >= 1
    assert all({"id", "title", "prompt", "difficulty"} <= p.keys() for p in problems)


async def test_only_the_round_interviewer_can_see_suggestions_or_select(client: AsyncClient):
    ctx = await _matched_pair(client)
    headers = {"Authorization": f"Bearer {ctx['token_interviewee']}"}

    res = await client.get(f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problems/suggestions", headers=headers)
    assert res.status_code == 403

    res2 = await client.post(f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem", json={"custom_text": "Reverse a string"}, headers=headers)
    assert res2.status_code == 403


async def test_selecting_from_the_bank_is_visible_to_both_before_the_round_starts(client: AsyncClient):
    ctx = await _matched_pair(client)
    suggestions = (await client.get(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problems/suggestions",
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )).json()["problems"]
    chosen = suggestions[0]

    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem",
        json={"problem_id": chosen["id"]},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 200

    for token in (ctx["token_interviewer"], ctx["token_interviewee"]):
        session = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers={"Authorization": f"Bearer {token}"})).json()
        assert session["status"] in ("CREATED", "PREPARATION")  # still hasn't started
        round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
        assert round1["problem"] == {
            "id": chosen["id"],
            "title": chosen["title"],
            "prompt": chosen["prompt"],
            "difficulty": chosen["difficulty"],
            "custom": False,
        }
        # Round 2 must stay untouched/hidden — selecting round 1 shouldn't leak it.
        round2 = next(r for r in session["rounds"] if r["round_number"] == 2)
        assert round2["problem"] is None


async def test_custom_question_is_visible_to_both_and_marked_custom(client: AsyncClient):
    ctx = await _matched_pair(client)
    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem",
        json={"custom_text": "Design a rate limiter."},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 200

    session = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers={"Authorization": f"Bearer {ctx['token_interviewee']}"})).json()
    round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
    assert round1["problem"]["custom"] is True
    assert round1["problem"]["prompt"] == "Design a rate limiter."
    assert round1["problem"]["id"] is None


async def test_selection_is_mutually_exclusive(client: AsyncClient):
    ctx = await _matched_pair(client)
    headers = {"Authorization": f"Bearer {ctx['token_interviewer']}"}
    endpoint = f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem"

    both = await client.post(endpoint, json={"problem_id": "not-a-real-check-yet", "custom_text": "x"}, headers=headers)
    assert both.status_code == 400

    neither = await client.post(endpoint, json={}, headers=headers)
    assert neither.status_code == 400


async def test_picking_a_problem_from_another_room_is_rejected(client: AsyncClient):
    ctx = await _matched_pair(client)
    rooms = (await client.get("/api/v1/rooms/")).json()["rooms"]
    other_room_suggestions = None
    for room in rooms:
        if room["id"] == ctx["room_id"]:
            continue
        # Need a round in that other room to legitimately query its bank; simplest
        # proxy is asking for a problem id that belongs to a different room than
        # this round's DSA room, which the seeded system-design/oop-lld rooms have.
        other_room_suggestions = room
        break
    assert other_room_suggestions is not None

    # Grab a real problem id from the OTHER room directly via a second matched
    # pair in that room, then try to apply it to the first round.
    suffix = uuid.uuid4().hex[:10]
    email_c, email_d = f"picker_c_{suffix}@example.com", f"picker_d_{suffix}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email_c, "password": "pass", "display_name": "C"})
    await client.post("/api/v1/auth/register", json={"email": email_d, "password": "pass", "display_name": "D"})
    token_c = (await client.post("/api/v1/auth/login", json={"email": email_c, "password": "pass"})).json()["access_token"]
    token_d = (await client.post("/api/v1/auth/login", json={"email": email_d, "password": "pass"})).json()["access_token"]
    id_c = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_c}"})).json()["id"]
    await client.post("/api/v1/matchmaking/join", json={"room_id": other_room_suggestions["id"], "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_c}"})
    res_d = await client.post("/api/v1/matchmaking/join", json={"room_id": other_room_suggestions["id"], "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_d}"})
    other_session_id = res_d.json()["match"]["match_id"]
    other_session = (await client.get(f"/api/v1/sessions/{other_session_id}", headers={"Authorization": f"Bearer {token_c}"})).json()
    other_round1 = next(r for r in other_session["rounds"] if r["round_number"] == 1)
    other_interviewer_id = next(uid for uid, role in other_round1["roles"].items() if role == "INTERVIEWER")
    other_token = token_c if other_interviewer_id == id_c else token_d
    other_suggestions = (await client.get(
        f"/api/v1/sessions/{other_session_id}/rounds/{other_round1['id']}/problems/suggestions",
        headers={"Authorization": f"Bearer {other_token}"},
    )).json()["problems"]
    foreign_problem_id = other_suggestions[0]["id"]

    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem",
        json={"problem_id": foreign_problem_id},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 404


async def test_cannot_pick_for_a_round_that_is_already_over(client: AsyncClient, db_session: AsyncSession):
    ctx = await _matched_pair(client)
    round_obj = (await db_session.execute(select(InterviewRound).where(InterviewRound.id == uuid.UUID(ctx["round_id"])))).scalar_one()
    round_obj.status = "COMPLETED"
    await db_session.commit()

    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem",
        json={"custom_text": "Too late"},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    assert res.status_code == 409


async def test_picking_a_problem_after_custom_text_overwrites_it(client: AsyncClient):
    ctx = await _matched_pair(client)
    headers = {"Authorization": f"Bearer {ctx['token_interviewer']}"}
    endpoint = f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem"

    await client.post(endpoint, json={"custom_text": "First draft question"}, headers=headers)
    suggestions = (await client.get(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problems/suggestions", headers=headers
    )).json()["problems"]
    await client.post(endpoint, json={"problem_id": suggestions[0]["id"]}, headers=headers)

    session = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers=headers)).json()
    round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
    assert round1["problem"]["custom"] is False
    assert round1["problem"]["id"] == suggestions[0]["id"]
