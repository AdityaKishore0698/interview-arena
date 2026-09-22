import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..core.database import AsyncSessionLocal
from ..core.redis import get_redis
from ..identity.streaks import record_checkin
from .models import InterviewRound, InterviewSession

logger = logging.getLogger(__name__)

import os
is_testing = os.environ.get("TESTING", "").lower() == "true"

# Modes (in seconds for easy testing vs real)
MODE_DURATIONS = {
    "QUICK": {
        "PREPARATION": 3 if is_testing else 30,
        "ROUND_ACTIVE": 15 if is_testing else 300,
        "ROUND_FEEDBACK": 10 if is_testing else 60
    },
    "STANDARD": {
        "PREPARATION": 5 if is_testing else 30,
        "ROUND_ACTIVE": 15 if is_testing else 900,
        "ROUND_FEEDBACK": 10 if is_testing else 120
    }
}

async def advance_state(session_id: str, is_guest: bool) -> bool:
    """Returns True if the session is still active, False if terminal."""
    redis = await get_redis()
    now = datetime.now(UTC)
    
    if not is_guest:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(InterviewSession)
                .options(selectinload(InterviewSession.participants), selectinload(InterviewSession.rounds).selectinload(InterviewRound.feedbacks))
                .where(InterviewSession.id == uuid.UUID(session_id))
            )
            session = result.scalars().first()
            if not session:
                return False
                
            if session.status in ["COMPLETED", "ABANDONED", "CANCELED"]:
                return False
                
            mode_dur = MODE_DURATIONS.get(session.mode, MODE_DURATIONS["STANDARD"])
            
            events_to_broadcast = []
            
            # Helper to broadcast
            def schedule_broadcast(event_name: str, payload: dict):
                events_to_broadcast.append((event_name, payload))
                
            def get_round(num):
                return next((r for r in session.rounds if r.round_number == num), None)
            
            # State transitions
            changed = False
            
            if session.status == "CREATED":
                session.status = "PREPARATION"
                session.started_at = now
                session.version += 1
                changed = True
                schedule_broadcast("SESSION_STARTED", {"status": "PREPARATION", "endsAt": (now + timedelta(seconds=mode_dur["PREPARATION"])).isoformat()})
                
            elif session.status == "PREPARATION":
                if session.started_at and (now - session.started_at).total_seconds() >= mode_dur["PREPARATION"]:
                    session.status = "ROUND_1_ACTIVE"
                    session.version += 1
                    r1 = get_round(1)
                    if r1:
                        r1.status = "ACTIVE"
                        r1.started_at = now
                    changed = True
                    schedule_broadcast("ROUND_STARTED", {"round": 1, "endsAt": (now + timedelta(seconds=mode_dur["ROUND_ACTIVE"])).isoformat()})
                    
            elif session.status == "ROUND_1_ACTIVE":
                r1 = get_round(1)
                if r1 and (now - r1.started_at).total_seconds() >= mode_dur["ROUND_ACTIVE"]:
                    session.status = "ROUND_1_FEEDBACK"
                    session.version += 1
                    r1.status = "FEEDBACK"
                    r1.ended_at = now
                    changed = True
                    schedule_broadcast("FEEDBACK_STARTED", {"round": 1, "endsAt": (now + timedelta(seconds=mode_dur["ROUND_FEEDBACK"])).isoformat()})
                    
            elif session.status == "ROUND_1_FEEDBACK":
                r1 = get_round(1)
                # Transition if time is up OR both feedbacks are submitted
                time_up = (now - r1.ended_at).total_seconds() >= mode_dur["ROUND_FEEDBACK"] if r1.ended_at else True
                both_submitted = r1 and len(r1.feedbacks) >= 2
                
                if time_up or both_submitted:
                    session.status = "ROUND_2_ACTIVE"
                    session.version += 1
                    if r1: r1.status = "COMPLETED"
                    r2 = get_round(2)
                    if r2:
                        r2.status = "ACTIVE"
                        r2.started_at = now
                    changed = True
                    schedule_broadcast("ROUND_STARTED", {"round": 2, "endsAt": (now + timedelta(seconds=mode_dur["ROUND_ACTIVE"])).isoformat()})
                    
            elif session.status == "ROUND_2_ACTIVE":
                r2 = get_round(2)
                if r2 and (now - r2.started_at).total_seconds() >= mode_dur["ROUND_ACTIVE"]:
                    session.status = "ROUND_2_FEEDBACK"
                    session.version += 1
                    r2.status = "FEEDBACK"
                    r2.ended_at = now
                    changed = True
                    schedule_broadcast("FEEDBACK_STARTED", {"round": 2, "endsAt": (now + timedelta(seconds=mode_dur["ROUND_FEEDBACK"])).isoformat()})
                    
            elif session.status == "ROUND_2_FEEDBACK":
                r2 = get_round(2)
                time_up = (now - r2.ended_at).total_seconds() >= mode_dur["ROUND_FEEDBACK"] if r2.ended_at else True
                both_submitted = r2 and len(r2.feedbacks) >= 2
                
                if time_up or both_submitted:
                    session.status = "COMPLETED"
                    session.completed_at = now
                    session.version += 1
                    if r2: r2.status = "COMPLETED"
                    changed = True
                    # Award interview-streak credit to both real (non-guest)
                    # participants in the same transaction as completion.
                    for p in session.participants:
                        await record_checkin(db, p.user_id, "interview")
                    schedule_broadcast("SESSION_COMPLETED", {})
            
            if changed:
                # Clear stale matchmaking locks for both participants
                if session.status in ["COMPLETED", "ABANDONED"]:
                    for p in session.participants:
                        await redis.delete(f"active_match:{p.user_id}")
                        await redis.delete(f"current_queue:{p.user_id}")
                await db.commit()
                
            for event_name, payload in events_to_broadcast:
                if "endsAt" in payload:
                    await redis.set(f"session:{session_id}:ends_at", payload["endsAt"], ex=86400)
                await redis.publish(
                    f"session:{session_id}:events",
                    json.dumps({"type": "EVENT", "event": event_name, "payload": payload})
                )
                
            return session.status not in ["COMPLETED", "ABANDONED", "CANCELED"]

    else:
        # Guest logic
        session_key = f"guest_session:{session_id}"
        guest_session = await redis.hgetall(session_key)
        if not guest_session:
            return False
            
        status = guest_session.get("status")
        if status in ["COMPLETED", "ABANDONED", "CANCELED"]:
            return False
            
        mode_dur = MODE_DURATIONS.get(guest_session.get("mode", "STANDARD"), MODE_DURATIONS["STANDARD"])
        version = int(guest_session.get("version", 1))
        
        async def broadcast(event_name: str, payload: dict):
            if "endsAt" in payload:
                await redis.set(f"session:{session_id}:ends_at", payload["endsAt"], ex=86400)
            await redis.publish(
                f"session:{session_id}:events",
                json.dumps({"type": "EVENT", "event": event_name, "payload": payload})
            )

        changed = False
        updates = {}
        
        # We need to track timestamps in Redis. They are stored as unix epoch strings
        def get_ts(key):
            val = guest_session.get(key)
            return datetime.fromtimestamp(float(val), tz=UTC) if val else now
            
        events_to_broadcast = []
        def schedule_broadcast(event_name: str, payload: dict):
            events_to_broadcast.append((event_name, payload))

        if status == "CREATED":
            status = "PREPARATION"
            updates["status"] = status
            updates["started_at"] = str(now.timestamp())
            changed = True
            schedule_broadcast("SESSION_STARTED", {"status": "PREPARATION", "endsAt": (now + timedelta(seconds=mode_dur["PREPARATION"])).isoformat()})
            
        elif status == "PREPARATION":
            started_at = get_ts("started_at")
            if (now - started_at).total_seconds() >= mode_dur["PREPARATION"]:
                status = "ROUND_1_ACTIVE"
                updates["status"] = status
                updates["round_1_status"] = "ACTIVE"
                updates["round_1_started_at"] = str(now.timestamp())
                changed = True
                schedule_broadcast("ROUND_STARTED", {"round": 1, "endsAt": (now + timedelta(seconds=mode_dur["ROUND_ACTIVE"])).isoformat()})
                
        elif status == "ROUND_1_ACTIVE":
            r1_started_at = get_ts("round_1_started_at")
            if (now - r1_started_at).total_seconds() >= mode_dur["ROUND_ACTIVE"]:
                status = "ROUND_1_FEEDBACK"
                updates["status"] = status
                updates["round_1_status"] = "FEEDBACK"
                updates["round_1_ended_at"] = str(now.timestamp())
                changed = True
                schedule_broadcast("FEEDBACK_STARTED", {"round": 1, "endsAt": (now + timedelta(seconds=mode_dur["ROUND_FEEDBACK"])).isoformat()})
                
        elif status == "ROUND_1_FEEDBACK":
            r1_ended = get_ts("round_1_ended_at")
            time_up = (now - r1_ended).total_seconds() >= mode_dur["ROUND_FEEDBACK"]
            # Check if both feedbacks are present
            user_a = guest_session.get("user_a")
            user_b = guest_session.get("user_b")
            both_submitted = ("feedback_1_" + user_a in guest_session) and ("feedback_1_" + user_b in guest_session)
            
            if time_up or both_submitted:
                status = "ROUND_2_ACTIVE"
                updates["status"] = status
                updates["round_1_status"] = "COMPLETED"
                updates["round_2_status"] = "ACTIVE"
                updates["round_2_started_at"] = str(now.timestamp())
                changed = True
                schedule_broadcast("ROUND_STARTED", {"round": 2, "endsAt": (now + timedelta(seconds=mode_dur["ROUND_ACTIVE"])).isoformat()})
                
        elif status == "ROUND_2_ACTIVE":
            r2_started = get_ts("round_2_started_at")
            if (now - r2_started).total_seconds() >= mode_dur["ROUND_ACTIVE"]:
                status = "ROUND_2_FEEDBACK"
                updates["status"] = status
                updates["round_2_status"] = "FEEDBACK"
                updates["round_2_ended_at"] = str(now.timestamp())
                changed = True
                schedule_broadcast("FEEDBACK_STARTED", {"round": 2, "endsAt": (now + timedelta(seconds=mode_dur["ROUND_FEEDBACK"])).isoformat()})
                
        elif status == "ROUND_2_FEEDBACK":
            r2_ended = get_ts("round_2_ended_at")
            time_up = (now - r2_ended).total_seconds() >= mode_dur["ROUND_FEEDBACK"]
            user_a = guest_session.get("user_a")
            user_b = guest_session.get("user_b")
            both_submitted = ("feedback_2_" + user_a in guest_session) and ("feedback_2_" + user_b in guest_session)
            
            if time_up or both_submitted:
                status = "COMPLETED"
                updates["status"] = status
                updates["round_2_status"] = "COMPLETED"
                updates["completed_at"] = str(now.timestamp())
                changed = True
                schedule_broadcast("SESSION_COMPLETED", {})
                
        if changed:
            updates["version"] = str(version + 1)
            await redis.hset(session_key, mapping=updates)
            if status in ("COMPLETED", "ABANDONED"):
                # Mirrors the registered-session cleanup above and the
                # explicit-leave path in SessionService.leave_session — without
                # this, a guest whose session ends naturally (rather than by
                # clicking Leave) keeps a stale active_match lock, and their
                # very next queue join is silently redirected back to this
                # same, already-finished session instead of starting a new one.
                user_a = guest_session.get("user_a")
                user_b = guest_session.get("user_b")
                for uid in (user_a, user_b):
                    if uid:
                        await redis.delete(f"active_match:{uid}")
                        await redis.delete(f"current_queue:{uid}")
            for event_name, payload in events_to_broadcast:
                if "endsAt" in payload:
                    await redis.set(f"session:{session_id}:ends_at", payload["endsAt"], ex=86400)
                await redis.publish(
                    f"session:{session_id}:events",
                    json.dumps({"type": "EVENT", "event": event_name, "payload": payload})
                )
            
        return status not in ["COMPLETED", "ABANDONED", "CANCELED"]

async def start_session_lifecycle(session_id: str, is_guest: bool = False):
    """
    Runs in the background and enforces the interview timer state machine.
    """
    logger.info(f"Starting lifecycle for session {session_id}")
    # In a real system, you would calculate the exact seconds until the next transition and sleep exactly that long.
    # For Phase 2B, polling every 2 seconds is acceptable.
    while True:
        try:
            active = await advance_state(session_id, is_guest)
            if not active:
                break
        except Exception as e:
            logger.error(f"Error in lifecycle loop for {session_id}: {e}")
            
        await asyncio.sleep(2)
