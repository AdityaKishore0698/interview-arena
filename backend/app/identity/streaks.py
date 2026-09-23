"""Daily login and interview streak tracking.

A "day" is a UTC calendar date, consistent with the rest of the app's
server-authoritative timing (interview round timers, reset-code expiry).
Known simplification: a user near a UTC midnight boundary may see their
streak roll over at a time that doesn't match their local midnight. Getting
this exactly right needs a per-user timezone, which the app doesn't collect.
"""
import uuid
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from .models import UserStreak

Kind = Literal["login", "interview"]


def _advance(count: int, last: date | None, longest: int, today: date) -> tuple[int, int, date]:
    """Pure streak-advance step, kept separate from I/O so every case (first
    check-in, same-day repeat, consecutive day, lapsed streak) is cheap to
    test without a database."""
    if last == today:
        return count, longest, last  # already counted today: no-op
    if last is not None and (today - last).days == 1:
        count += 1
    else:
        count = 1  # first check-in ever, or the streak lapsed
    longest = max(longest, count)
    return count, longest, today


async def record_checkin(db: AsyncSession, user_id: uuid.UUID, kind: Kind) -> UserStreak:
    """Advance the given streak for `user_id` if today hasn't been counted
    yet, creating the row on first use. Does not commit — the caller controls
    the transaction boundary (this is called both from a dedicated endpoint
    and from inside the interview-lifecycle transition)."""
    row = await db.get(UserStreak, user_id)
    if row is None:
        # Pass the counters explicitly rather than relying on the column
        # defaults: SQLAlchemy only applies `default=` at flush time, and
        # this function reads the fields on `row` before ever flushing.
        row = UserStreak(
            user_id=user_id,
            login_streak=0,
            longest_login_streak=0,
            interview_streak=0,
            longest_interview_streak=0,
        )
        db.add(row)

    today = datetime.now(UTC).date()
    if kind == "login":
        row.login_streak, row.longest_login_streak, row.login_streak_last_date = _advance(
            row.login_streak, row.login_streak_last_date, row.longest_login_streak, today
        )
    else:
        row.interview_streak, row.longest_interview_streak, row.interview_streak_last_date = _advance(
            row.interview_streak, row.interview_streak_last_date, row.longest_interview_streak, today
        )
    return row
