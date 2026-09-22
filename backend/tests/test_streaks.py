"""Daily login/interview streaks.

The interview-streak-on-completion test bypasses the client/db_session
fixtures for its setup and talks to AsyncSessionLocal directly. That's not a
workaround: app/interview/lifecycle.py's background completion logic always
runs on its own connection (AsyncSessionLocal, bound to the real engine), not
on the request-scoped, rollback-on-teardown session the other fixtures give
`client`. Driving it through `client` would silently see none of the setup,
since Postgres won't show one connection's uncommitted transaction to
another. Because this test commits for real, it cleans up after itself.
"""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.identity.models import Profile, User, UserStreak
from app.identity.streaks import record_checkin
from app.interview.lifecycle import advance_state
from app.interview.models import (
    InterviewParticipant,
    InterviewRoom,
    InterviewRound,
    InterviewSession,
)

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str) -> tuple[str, str]:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "pass", "display_name": "Streaker"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "pass"})
    token = login.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]


# ---- pure/direct logic ------------------------------------------------

async def test_record_checkin_first_time(db_session: AsyncSession, client: AsyncClient):
    _token, user_id = await _register(client, f"streak_{uuid.uuid4()}@example.com")
    row = await record_checkin(db_session, uuid.UUID(user_id), "login")
    await db_session.commit()
    assert row.login_streak == 1
    assert row.longest_login_streak == 1
    assert row.login_streak_last_date == datetime.now(UTC).date()


async def test_record_checkin_same_day_is_idempotent(db_session: AsyncSession, client: AsyncClient):
    _token, user_id = await _register(client, f"streak_{uuid.uuid4()}@example.com")
    uid = uuid.UUID(user_id)
    await record_checkin(db_session, uid, "login")
    row = await record_checkin(db_session, uid, "login")
    await db_session.commit()
    assert row.login_streak == 1


async def test_record_checkin_consecutive_day_increments(db_session: AsyncSession, client: AsyncClient):
    _token, user_id = await _register(client, f"streak_{uuid.uuid4()}@example.com")
    uid = uuid.UUID(user_id)
    row = await record_checkin(db_session, uid, "login")
    row.login_streak_last_date = datetime.now(UTC).date() - timedelta(days=1)
    await db_session.flush()

    row = await record_checkin(db_session, uid, "login")
    await db_session.commit()
    assert row.login_streak == 2
    assert row.longest_login_streak == 2


async def test_record_checkin_gap_resets_but_keeps_longest(db_session: AsyncSession, client: AsyncClient):
    _token, user_id = await _register(client, f"streak_{uuid.uuid4()}@example.com")
    uid = uuid.UUID(user_id)
    row = await record_checkin(db_session, uid, "login")
    row.login_streak = 5
    row.longest_login_streak = 5
    row.login_streak_last_date = datetime.now(UTC).date() - timedelta(days=3)
    await db_session.flush()

    row = await record_checkin(db_session, uid, "login")
    await db_session.commit()
    assert row.login_streak == 1
    assert row.longest_login_streak == 5  # the record isn't erased by a lapse


# ---- endpoints ----------------------------------------------------------

async def test_checkin_endpoint_returns_updated_streak(client: AsyncClient):
    token, _user_id = await _register(client, f"streak_{uuid.uuid4()}@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post("/api/v1/auth/streaks/checkin", headers=headers)
    assert res.status_code == 200
    assert res.json() == {
        "login_streak": 1,
        "longest_login_streak": 1,
        "interview_streak": 0,
        "longest_interview_streak": 0,
    }

    # Same day again: still 1, not 2.
    res2 = await client.post("/api/v1/auth/streaks/checkin", headers=headers)
    assert res2.json()["login_streak"] == 1


async def test_get_streak_before_any_checkin_returns_zeros(client: AsyncClient):
    token, _user_id = await _register(client, f"streak_{uuid.uuid4()}@example.com")
    res = await client.get("/api/v1/auth/streaks/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json() == {
        "login_streak": 0,
        "longest_login_streak": 0,
        "interview_streak": 0,
        "longest_interview_streak": 0,
    }


async def test_guest_cannot_checkin(client: AsyncClient):
    guest = await client.post("/api/v1/auth/guest")
    token = guest.json()["access_token"]
    res = await client.post("/api/v1/auth/streaks/checkin", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


async def test_guest_streak_read_is_zeros_not_error(client: AsyncClient):
    guest = await client.post("/api/v1/auth/guest")
    token = guest.json()["access_token"]
    res = await client.get("/api/v1/auth/streaks/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["login_streak"] == 0


# ---- interview-streak hook on session completion -------------------------

async def test_interview_streak_increments_on_session_completion():
    async with AsyncSessionLocal() as db:
        room = (await db.execute(select(InterviewRoom).limit(1))).scalars().first()
        assert room is not None, "expected the seeded rooms to exist"

        users = []
        for i in range(2):
            u = User(email=f"streak_complete_{uuid.uuid4()}@example.com", password_hash="x", is_verified=True)
            u.profile = Profile(display_name=f"Streak Complete {i}")
            db.add(u)
            users.append(u)
        await db.flush()

        session = InterviewSession(room_id=room.id, mode="STANDARD", status="ROUND_2_FEEDBACK")
        db.add(session)
        await db.flush()

        participants = [
            InterviewParticipant(session_id=session.id, user_id=u.id, seat=i + 1)
            for i, u in enumerate(users)
        ]
        db.add_all(participants)
        await db.flush()

        # Backdated well past the feedback window, so the very next tick
        # completes the session on time_up alone (no feedback rows needed —
        # those are exercised by the existing feedback tests, not this one).
        past = datetime.now(UTC) - timedelta(hours=1)
        db.add_all([
            InterviewRound(session_id=session.id, round_number=1, status="COMPLETED", started_at=past, ended_at=past),
            InterviewRound(session_id=session.id, round_number=2, status="FEEDBACK", started_at=past, ended_at=past),
        ])
        session_id = str(session.id)
        user_ids = [u.id for u in users]
        await db.commit()

    try:
        active = await advance_state(session_id, is_guest=False)
        assert active is False  # COMPLETED is terminal

        async with AsyncSessionLocal() as db:
            refreshed = (
                await db.execute(select(InterviewSession).where(InterviewSession.id == uuid.UUID(session_id)))
            ).scalar_one()
            assert refreshed.status == "COMPLETED"

            for uid in user_ids:
                streak = await db.get(UserStreak, uid)
                assert streak is not None, "record_checkin should have created a row"
                assert streak.interview_streak == 1
                assert streak.longest_interview_streak == 1
    finally:
        async with AsyncSessionLocal() as db:
            sess = await db.get(InterviewSession, uuid.UUID(session_id))
            if sess:
                await db.delete(sess)  # cascades to participants/rounds/round_participants
            for uid in user_ids:
                u = await db.get(User, uid)
                if u:
                    await db.delete(u)  # cascades to profile + user_streaks
            await db.commit()
