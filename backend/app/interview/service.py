import hashlib
import json
import uuid
from typing import Any

from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .models import (
    InterviewProblem,
    InterviewRoom,
    InterviewRound,
    InterviewSession,
)

# Round/session statuses at or past which a round's problem is authoritative
# and therefore safe to reveal to both participants.
_STARTED_ROUND_STATUSES = {"ACTIVE", "FEEDBACK", "COMPLETED"}


class SessionService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def _load_room(self, room_id: str | None) -> dict[str, Any] | None:
        if not room_id:
            return None
        try:
            room_uuid = uuid.UUID(str(room_id))
        except (ValueError, TypeError):
            return None
        room = (
            await self.db.execute(select(InterviewRoom).where(InterviewRoom.id == room_uuid))
        ).scalar_one_or_none()
        if not room:
            return None
        return {
            "id": str(room.id),
            "slug": room.slug,
            "name": room.name,
            "difficulty": room.difficulty,
            "description": room.description,
        }

    async def _load_problems_by_slot(self, room_id: str | None) -> dict[int, list[InterviewProblem]]:
        if not room_id:
            return {}
        try:
            room_uuid = uuid.UUID(str(room_id))
        except (ValueError, TypeError):
            return {}
        rows = (
            await self.db.execute(
                select(InterviewProblem)
                .where(InterviewProblem.room_id == room_uuid)
                .order_by(InterviewProblem.slot, InterviewProblem.title)
            )
        ).scalars().all()
        by_slot: dict[int, list[InterviewProblem]] = {}
        for p in rows:
            by_slot.setdefault(p.slot, []).append(p)
        return by_slot

    @staticmethod
    def _pick_problem(
        problems_by_slot: dict[int, list[InterviewProblem]], session_id: str, round_number: int
    ) -> dict[str, Any] | None:
        candidates = problems_by_slot.get(round_number) or []
        if not candidates:
            return None
        seed = int(hashlib.sha256(f"{session_id}:{round_number}".encode()).hexdigest(), 16)
        chosen = candidates[seed % len(candidates)]
        return {
            "id": str(chosen.id),
            "title": chosen.title,
            "prompt": chosen.prompt,
            "difficulty": chosen.difficulty,
        }

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        # 1. Try PostgreSQL (Registered users)
        try:
            session_uuid = uuid.UUID(session_id)
            result = await self.db.execute(
                select(InterviewSession)
                .options(
                    selectinload(InterviewSession.participants),
                    selectinload(InterviewSession.rounds).selectinload(InterviewRound.round_participants),
                    selectinload(InterviewSession.rounds).selectinload(InterviewRound.feedbacks),
                )
                .where(InterviewSession.id == session_uuid)
            )
            session = result.scalar_one_or_none()
            if session:
                participant_map = {str(p.id): str(p.user_id) for p in session.participants}
                room = await self._load_room(str(session.room_id))
                problems_by_slot = await self._load_problems_by_slot(str(session.room_id))

                rounds_payload = []
                for r in sorted(session.rounds, key=lambda x: x.round_number):
                    round_started = r.status in _STARTED_ROUND_STATUSES or r.started_at is not None
                    round_dict = {
                        "id": str(r.id),
                        "round_number": r.round_number,
                        "status": r.status,
                        "roles": {participant_map[str(rp.participant_id)]: rp.role for rp in r.round_participants},
                        "problem": self._pick_problem(problems_by_slot, str(session.id), r.round_number) if round_started else None,
                        "feedbacks": [
                            {
                                "evaluated_role": fb.evaluated_role,
                                "scores": fb.scores,
                                "comments": fb.comments,
                                "giver_user_id": participant_map.get(str(fb.giver_participant_id)),
                                "receiver_user_id": participant_map.get(str(fb.receiver_participant_id)),
                            }
                            for fb in r.feedbacks
                        ],
                    }
                    rounds_payload.append(round_dict)

                payload = {
                    "id": str(session.id),
                    "room_id": str(session.room_id),
                    "room": room,
                    "mode": session.mode,
                    "status": session.status,
                    "version": session.version,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "participants": [
                        {"id": str(p.id), "user_id": str(p.user_id), "seat": p.seat}
                        for p in session.participants
                    ],
                    "rounds": rounds_payload,
                }
                ends_at = await self.redis.get(f"session:{session_id}:ends_at")
                if ends_at:
                    payload["current_ends_at"] = ends_at
                return payload
        except ValueError:
            pass # Invalid UUID, maybe check Redis anyway

        # 2. Try Redis (Guest users)
        session_key = f"guest_session:{session_id}"
        guest_session = await self.redis.hgetall(session_key)
        if guest_session:
            # Redis hgetall returns bytes if decode_responses is not set,
            # but we use decode_responses=True in get_redis().
            user_a = guest_session.get("user_a")
            user_b = guest_session.get("user_b")
            room_id = guest_session.get("room_id")
            room = await self._load_room(room_id)
            problems_by_slot = await self._load_problems_by_slot(room_id)

            round_roles = {
                1: {user_a: "INTERVIEWER", user_b: "INTERVIEWEE"},
                2: {user_a: "INTERVIEWEE", user_b: "INTERVIEWER"},
            }

            rounds_payload = []
            for n in (1, 2):
                status = guest_session.get(f"round_{n}_status", "PENDING")
                round_started = (
                    status in _STARTED_ROUND_STATUSES
                    or guest_session.get(f"round_{n}_started_at") is not None
                )
                feedbacks = []
                for giver, receiver in ((user_a, user_b), (user_b, user_a)):
                    raw = guest_session.get(f"feedback_{n}_{giver}")
                    if not raw:
                        continue
                    try:
                        parsed = json.loads(raw)
                    except (ValueError, TypeError):
                        continue
                    feedbacks.append({
                        "evaluated_role": round_roles[n].get(receiver),
                        "scores": parsed.get("scores"),
                        "comments": parsed.get("comments"),
                        "giver_user_id": giver,
                        "receiver_user_id": receiver,
                    })
                rounds_payload.append({
                    "id": f"round_{n}_{session_id}",
                    "round_number": n,
                    "status": status,
                    "roles": round_roles[n],
                    "problem": self._pick_problem(problems_by_slot, session_id, n) if round_started else None,
                    "feedbacks": feedbacks,
                })

            payload = {
                "id": session_id,
                "room_id": room_id,
                "room": room,
                "mode": guest_session.get("mode"),
                "status": guest_session.get("status"),
                "version": int(guest_session.get("version", 1)),
                "created_at": guest_session.get("created_at"),
                "participants": [
                    {"user_id": user_a, "seat": 1, "id": user_a},
                    {"user_id": user_b, "seat": 2, "id": user_b},
                ],
                "rounds": rounds_payload,
            }
            ends_at = await self.redis.get(f"session:{session_id}:ends_at")
            if ends_at:
                payload["current_ends_at"] = ends_at
            return payload

        return None


    async def leave_session(self, session_id: str, user_id: str) -> None:
        try:
            session_uuid = uuid.UUID(session_id)
            result = await self.db.execute(select(InterviewSession).where(InterviewSession.id == session_uuid))
            session = result.scalars().first()
            if session:
                if session.status not in ["COMPLETED", "ABANDONED", "CANCELED"]:
                    session.status = "ABANDONED"
                    import datetime
                    session.abandoned_at = datetime.datetime.now(datetime.UTC)
                    session.version += 1
                    await self.db.commit()
                    
                    # Clear stale matchmaking locks for both participants
                    for p in session.participants:
                        await self.redis.delete(f"active_match:{p.user_id}")
                        await self.redis.delete(f"current_queue:{p.user_id}")
                        
                    import json
                    await self.redis.publish(
                        f"session:{session_id}:events",
                        json.dumps({
                            "type": "EVENT",
                            "event": "SESSION_ABANDONED",
                            "payload": {"reason": "USER_LEFT", "userId": user_id}
                        })
                    )
                return
        except ValueError:
            pass

        # Guest fallback
        session_key = f"guest_session:{session_id}"
        guest_session = await self.redis.hgetall(session_key)
        if guest_session and guest_session.get("status") not in ["COMPLETED", "ABANDONED", "CANCELED"]:
            await self.redis.hset(session_key, "status", "ABANDONED")
            version = int(guest_session.get("version", 1)) + 1
            await self.redis.hset(session_key, "version", str(version))
            
            await self.redis.delete(f"active_match:{guest_session.get('user_a')}")
            await self.redis.delete(f"active_match:{guest_session.get('user_b')}")
            await self.redis.delete(f"current_queue:{guest_session.get('user_a')}")
            await self.redis.delete(f"current_queue:{guest_session.get('user_b')}")
            
            import json
            await self.redis.publish(
                f"session:{session_id}:events",
                json.dumps({
                    "type": "EVENT",
                    "event": "SESSION_ABANDONED",
                    "payload": {"reason": "USER_LEFT", "userId": user_id}
                })
            )

    async def submit_feedback(self, session_id: str, round_id: str, user_id: str, scores: dict, comments: str | None) -> None:
        # We need to distinguish between guest and registered.
        try:
            session_uuid = uuid.UUID(session_id)
            # Registered logic
            from sqlalchemy.orm import selectinload

            from .models import (
                Feedback,
                InterviewRound,
                RoundParticipant,
            )
            
            # Ensure the session and round exist
            result = await self.db.execute(
                select(InterviewRound)
                .options(selectinload(InterviewRound.round_participants).selectinload(RoundParticipant.participant))
                .where(InterviewRound.id == uuid.UUID(round_id))
            )
            round_obj = result.scalars().first()
            if not round_obj:
                raise HTTPException(status_code=404, detail="Round not found")
                
            giver_part = next((rp.participant for rp in round_obj.round_participants if str(rp.participant.user_id) == user_id), None)
            if not giver_part:
                raise HTTPException(status_code=403, detail="User not in round")
                
            receiver_rp = next((rp for rp in round_obj.round_participants if str(rp.participant.user_id) != user_id), None)
            if not receiver_rp:
                raise HTTPException(status_code=404, detail="No opponent found")
            
            receiver_part = receiver_rp.participant
            evaluated_role = receiver_rp.role

            # Check if feedback already submitted
            existing = await self.db.execute(
                select(Feedback).where(
                    (Feedback.round_id == round_obj.id) & 
                    (Feedback.giver_participant_id == giver_part.id)
                )
            )
            if existing.scalars().first():
                raise HTTPException(status_code=409, detail="Feedback already submitted")

            fb = Feedback(
                round_id=round_obj.id,
                giver_participant_id=giver_part.id,
                receiver_participant_id=receiver_part.id,
                evaluated_role=evaluated_role,
                status="SUBMITTED",
                scores=scores,
                comments=comments
            )
            import datetime
            fb.submitted_at = datetime.datetime.now(datetime.UTC)
            self.db.add(fb)
            
            # Increment session version
            sess_result = await self.db.execute(select(InterviewSession).where(InterviewSession.id == session_uuid))
            sess = sess_result.scalars().first()
            if sess:
                sess.version += 1
                
            await self.db.commit()
            
            import json
            await self.redis.publish(
                f"session:{session_id}:events",
                json.dumps({
                    "type": "EVENT",
                    "event": "FEEDBACK_SUBMITTED",
                    "payload": {"userId": user_id, "roundId": round_id}
                })
            )
            return

        except ValueError as e:
            if str(e) in ["Round not found", "User not in round", "No opponent found", "Feedback already submitted"]:
                raise
            # fallback to guest

        # Guest logic
        # For guest, round_id is round_1_{session_id} or round_2_{session_id}
        round_num = 1 if "round_1" in round_id else 2
        session_key = f"guest_session:{session_id}"
        
        has_fb = await self.redis.hget(session_key, f"feedback_{round_num}_{user_id}")
        if has_fb:
            raise HTTPException(status_code=409, detail="Feedback already submitted")
            
        import json
        await self.redis.hset(session_key, f"feedback_{round_num}_{user_id}", json.dumps({
            "scores": scores, "comments": comments
        }))
        
        v = await self.redis.hget(session_key, "version")
        await self.redis.hset(session_key, "version", str(int(v or 1) + 1))
        
        await self.redis.publish(
            f"session:{session_id}:events",
            json.dumps({
                "type": "EVENT",
                "event": "FEEDBACK_SUBMITTED",
                "payload": {"userId": user_id, "roundId": round_id}
            })
        )
