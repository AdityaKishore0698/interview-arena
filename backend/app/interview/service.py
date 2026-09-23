import hashlib
import json
import uuid
from typing import Any

import httpx
from fastapi import HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from . import code_execution
from .models import (
    InterviewProblem,
    InterviewRoom,
    InterviewRound,
    InterviewSession,
    ProblemTestCase,
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
            "custom": False,
        }

    @staticmethod
    def _resolve_problem(
        problem_id: uuid.UUID | None,
        custom_text: str | None,
        problems_by_slot: dict[int, list[InterviewProblem]],
        session_id: str,
        round_number: int,
        round_started: bool,
    ) -> dict[str, Any] | None:
        """An interviewer's explicit pick (from the bank or free-form) always
        wins, and is visible as soon as it's made — even before the round
        starts, since that's the whole point of picking ahead of time.
        Otherwise, once the round has actually started, fall back to the
        existing deterministic auto-pick: picking is a suggestion, not
        mandatory, so an interviewer who never bothers sees no change.

        Takes plain values rather than an ORM object so both the registered
        (Postgres row) and guest (Redis hash) round representations can share
        this one resolution rule."""
        if problem_id is not None:
            for candidates in problems_by_slot.values():
                for p in candidates:
                    if p.id == problem_id:
                        return {
                            "id": str(p.id),
                            "title": p.title,
                            "prompt": p.prompt,
                            "difficulty": p.difficulty,
                            "custom": False,
                        }
            return None  # the chosen problem was deleted; FK is ON DELETE SET NULL so this heals itself
        if custom_text:
            return {
                "id": None,
                "title": "Interviewer's question",
                "prompt": custom_text,
                "difficulty": None,
                "custom": True,
            }
        if round_started:
            return SessionService._pick_problem(problems_by_slot, session_id, round_number)
        return None

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
                        "problem": self._resolve_problem(
                            r.problem_id, r.custom_problem_text, problems_by_slot, str(session.id), r.round_number, round_started
                        ),
                        "submitted_code": r.submitted_code,
                        "submitted_language": r.submitted_language,
                        "code_submitted_at": r.code_submitted_at.isoformat() if r.code_submitted_at else None,
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
                    "problem": self._resolve_problem(
                        uuid.UUID(guest_session[f"round_{n}_problem_id"]) if guest_session.get(f"round_{n}_problem_id") else None,
                        guest_session.get(f"round_{n}_custom_text") or None,
                        problems_by_slot, session_id, n, round_started,
                    ),
                    "submitted_code": guest_session.get(f"round_{n}_code") or None,
                    "submitted_language": guest_session.get(f"round_{n}_code_language") or None,
                    "code_submitted_at": guest_session.get(f"round_{n}_code_submitted_at") or None,
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

    async def _get_round_for_interviewer(self, round_id: str, user_id: str) -> InterviewRound:
        """Loads a round and confirms the caller is its interviewer. Shared by
        both the suggestions read and the selection write."""
        try:
            round_uuid = uuid.UUID(round_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=404, detail="Round not found")

        from .models import RoundParticipant

        result = await self.db.execute(
            select(InterviewRound)
            .options(
                selectinload(InterviewRound.round_participants).selectinload(RoundParticipant.participant),
                selectinload(InterviewRound.session),
            )
            .where(InterviewRound.id == round_uuid)
        )
        round_obj = result.scalars().first()
        if not round_obj:
            raise HTTPException(status_code=404, detail="Round not found")

        my_role = next(
            (rp.role for rp in round_obj.round_participants if str(rp.participant.user_id) == user_id),
            None,
        )
        if my_role != "INTERVIEWER":
            raise HTTPException(status_code=403, detail="Only this round's interviewer can do this")
        return round_obj

    @staticmethod
    def _parse_guest_round_id(round_id: str) -> tuple[str, int] | None:
        """Guest round ids look like 'round_1_<session_id>' / 'round_2_<session_id>'
        (see the guest branch of get_session) — a real round's UUID can never
        take that form, so this is an unambiguous way to tell the two apart.
        Returns (session_id, round_number), or None if this isn't a guest id."""
        for n in (1, 2):
            prefix = f"round_{n}_"
            if round_id.startswith(prefix):
                return round_id[len(prefix):], n
        return None

    @staticmethod
    def _require_guest_interviewer(guest_session: dict, user_id: str, round_number: int) -> None:
        # Mirrors get_session's round_roles convention: user_a interviews in
        # round 1, user_b in round 2 (roles reverse the same way as for
        # registered sessions — this isn't stored separately, just derived).
        interviewer = guest_session.get("user_a") if round_number == 1 else guest_session.get("user_b")
        if user_id != interviewer:
            raise HTTPException(status_code=403, detail="Only this round's interviewer can do this")

    async def get_problem_suggestions(self, round_id: str, user_id: str) -> list[dict[str, Any]]:
        """Problems from the round's room+slot, for its interviewer to
        optionally pick from — registered and guest sessions alike."""
        guest = self._parse_guest_round_id(round_id)
        if guest:
            session_id, round_number = guest
            guest_session = await self.redis.hgetall(f"guest_session:{session_id}")
            if not guest_session:
                raise HTTPException(status_code=404, detail="Round not found")
            self._require_guest_interviewer(guest_session, user_id, round_number)
            problems_by_slot = await self._load_problems_by_slot(guest_session.get("room_id"))
            candidates = problems_by_slot.get(round_number) or []
            return [
                {"id": str(p.id), "title": p.title, "prompt": p.prompt, "difficulty": p.difficulty}
                for p in candidates
            ]

        round_obj = await self._get_round_for_interviewer(round_id, user_id)
        problems_by_slot = await self._load_problems_by_slot(str(round_obj.session.room_id))
        candidates = problems_by_slot.get(round_obj.round_number) or []
        return [
            {"id": str(p.id), "title": p.title, "prompt": p.prompt, "difficulty": p.difficulty}
            for p in candidates
        ]

    async def select_problem(
        self, round_id: str, user_id: str, problem_id: str | None, custom_text: str | None
    ) -> None:
        """Only the round's interviewer may pick, and only before that round
        is over. Picking is a suggestion aid, not a commitment made ahead of
        time, so it stays changeable right up until then."""
        guest = self._parse_guest_round_id(round_id)
        if guest:
            await self._select_problem_guest(round_id, guest, user_id, problem_id, custom_text)
            return

        round_obj = await self._get_round_for_interviewer(round_id, user_id)
        if round_obj.status == "COMPLETED":
            raise HTTPException(status_code=409, detail="This round is already over")

        if bool(problem_id) == bool(custom_text):
            raise HTTPException(status_code=400, detail="Provide exactly one of problem_id or custom_text")

        if problem_id:
            try:
                problem_uuid = uuid.UUID(problem_id)
            except (ValueError, TypeError):
                raise HTTPException(status_code=404, detail="Problem not found for this room")
            problem = await self.db.get(InterviewProblem, problem_uuid)
            if not problem or problem.room_id != round_obj.session.room_id:
                raise HTTPException(status_code=404, detail="Problem not found for this room")
            round_obj.problem_id = problem.id
            round_obj.custom_problem_text = None
        else:
            text = (custom_text or "").strip()
            if not text or len(text) > 2000:
                raise HTTPException(status_code=400, detail="custom_text must be 1-2000 characters")
            round_obj.custom_problem_text = text
            round_obj.problem_id = None

        session_result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == round_obj.session_id)
        )
        session = session_result.scalars().first()
        if session:
            session.version += 1
        await self.db.commit()

        await self.redis.publish(
            f"session:{round_obj.session_id}:events",
            json.dumps({"type": "EVENT", "event": "SESSION_UPDATED", "payload": {"roundId": round_id}})
        )

    async def _select_problem_guest(
        self, round_id: str, guest: tuple[str, int], user_id: str, problem_id: str | None, custom_text: str | None
    ) -> None:
        session_id, round_number = guest
        session_key = f"guest_session:{session_id}"
        guest_session = await self.redis.hgetall(session_key)
        if not guest_session:
            raise HTTPException(status_code=404, detail="Round not found")
        self._require_guest_interviewer(guest_session, user_id, round_number)
        if guest_session.get(f"round_{round_number}_status") == "COMPLETED":
            raise HTTPException(status_code=409, detail="This round is already over")

        if bool(problem_id) == bool(custom_text):
            raise HTTPException(status_code=400, detail="Provide exactly one of problem_id or custom_text")

        updates: dict[str, str] = {}
        if problem_id:
            try:
                problem_uuid = uuid.UUID(problem_id)
            except (ValueError, TypeError):
                raise HTTPException(status_code=404, detail="Problem not found for this room")
            problem = await self.db.get(InterviewProblem, problem_uuid)
            if not problem or str(problem.room_id) != guest_session.get("room_id"):
                raise HTTPException(status_code=404, detail="Problem not found for this room")
            updates[f"round_{round_number}_problem_id"] = str(problem.id)
            updates[f"round_{round_number}_custom_text"] = ""  # Redis hash fields can't be unset in place; empty means "not set", same convention _resolve_problem expects
        else:
            text = (custom_text or "").strip()
            if not text or len(text) > 2000:
                raise HTTPException(status_code=400, detail="custom_text must be 1-2000 characters")
            updates[f"round_{round_number}_custom_text"] = text
            updates[f"round_{round_number}_problem_id"] = ""

        updates["version"] = str(int(guest_session.get("version", 1)) + 1)
        await self.redis.hset(session_key, mapping=updates)
        await self.redis.publish(
            f"session:{session_id}:events",
            json.dumps({"type": "EVENT", "event": "SESSION_UPDATED", "payload": {"roundId": round_id}})
        )

    async def _get_round_for_interviewee(self, round_id: str, user_id: str) -> InterviewRound:
        """Mirrors _get_round_for_interviewer — the code editor is the
        interviewee's tool, so only they may run or submit code for a round."""
        try:
            round_uuid = uuid.UUID(round_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=404, detail="Round not found")

        from .models import RoundParticipant

        result = await self.db.execute(
            select(InterviewRound)
            .options(
                selectinload(InterviewRound.round_participants).selectinload(RoundParticipant.participant),
                selectinload(InterviewRound.session),
            )
            .where(InterviewRound.id == round_uuid)
        )
        round_obj = result.scalars().first()
        if not round_obj:
            raise HTTPException(status_code=404, detail="Round not found")

        my_role = next(
            (rp.role for rp in round_obj.round_participants if str(rp.participant.user_id) == user_id),
            None,
        )
        if my_role != "INTERVIEWEE":
            raise HTTPException(status_code=403, detail="Only this round's interviewee can do this")
        return round_obj

    @staticmethod
    def _require_guest_interviewee(guest_session: dict, user_id: str, round_number: int) -> None:
        # Inverse of _require_guest_interviewer's convention: user_a is the
        # interviewer in round 1 (so user_b is the interviewee), and roles
        # reverse for round 2.
        interviewee = guest_session.get("user_b") if round_number == 1 else guest_session.get("user_a")
        if user_id != interviewee:
            raise HTTPException(status_code=403, detail="Only this round's interviewee can do this")

    async def _resolve_test_cases(self, problem_id: uuid.UUID | None) -> list[ProblemTestCase]:
        if problem_id is None:
            return []
        result = await self.db.execute(
            select(ProblemTestCase).where(ProblemTestCase.problem_id == problem_id)
        )
        return list(result.scalars().all())

    async def run_code_against_tests(
        self, round_id: str, user_id: str, language: str, code: str
    ) -> dict[str, Any]:
        """Runs the interviewee's code against the round's problem's sample
        test cases (DSA problems only — anything else simply has none seeded,
        so this naturally scopes itself without a hardcoded room check)."""
        if language not in code_execution.SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail="Unsupported language")
        if len(code) > 50_000:
            raise HTTPException(status_code=400, detail="Code is too long")

        guest = self._parse_guest_round_id(round_id)
        if guest:
            session_id, round_number = guest
            guest_session = await self.redis.hgetall(f"guest_session:{session_id}")
            if not guest_session:
                raise HTTPException(status_code=404, detail="Round not found")
            self._require_guest_interviewee(guest_session, user_id, round_number)
            raw_problem_id = guest_session.get(f"round_{round_number}_problem_id")
            problem_id = uuid.UUID(raw_problem_id) if raw_problem_id else None
        else:
            round_obj = await self._get_round_for_interviewee(round_id, user_id)
            problem_id = round_obj.problem_id

        test_cases = await self._resolve_test_cases(problem_id)
        if not test_cases:
            raise HTTPException(status_code=400, detail="This problem has no test cases to run against")

        results = []
        for tc in test_cases:
            try:
                outcome = await code_execution.run_code(language, code, tc.input)
            except RuntimeError as e:
                # Missing API key — a setup problem, not the candidate's code.
                raise HTTPException(status_code=503, detail=str(e))
            except httpx.HTTPError:
                raise HTTPException(status_code=502, detail="The code execution service is unavailable right now — try again in a moment.")
            actual = outcome.stdout.strip()
            expected = tc.expected_output.strip()
            results.append({
                "input": tc.input,
                "expected_output": tc.expected_output,
                "actual_output": outcome.stdout,
                "stderr": outcome.stderr,
                "passed": actual == expected and not outcome.timed_out,
                "timed_out": outcome.timed_out,
            })
        return {"results": results, "passed_count": sum(1 for r in results if r["passed"]), "total": len(results)}

    async def submit_code(self, round_id: str, user_id: str, language: str, code: str) -> None:
        """Persists the interviewee's code as this round's single latest
        submission and notifies the interviewer over the session's WS
        channel — kept afterward as part of interview history, like feedback."""
        if language not in code_execution.SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail="Unsupported language")
        if len(code) > 50_000:
            raise HTTPException(status_code=400, detail="Code is too long")

        import datetime

        guest = self._parse_guest_round_id(round_id)
        if guest:
            session_id, round_number = guest
            session_key = f"guest_session:{session_id}"
            guest_session = await self.redis.hgetall(session_key)
            if not guest_session:
                raise HTTPException(status_code=404, detail="Round not found")
            self._require_guest_interviewee(guest_session, user_id, round_number)

            updates = {
                f"round_{round_number}_code": code,
                f"round_{round_number}_code_language": language,
                f"round_{round_number}_code_submitted_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "version": str(int(guest_session.get("version", 1)) + 1),
            }
            await self.redis.hset(session_key, mapping=updates)
            await self.redis.publish(
                f"session:{session_id}:events",
                json.dumps({"type": "EVENT", "event": "CODE_SUBMITTED", "payload": {"roundId": round_id}})
            )
            return

        round_obj = await self._get_round_for_interviewee(round_id, user_id)
        round_obj.submitted_code = code
        round_obj.submitted_language = language
        round_obj.code_submitted_at = datetime.datetime.now(datetime.UTC)

        session_result = await self.db.execute(
            select(InterviewSession).where(InterviewSession.id == round_obj.session_id)
        )
        session = session_result.scalars().first()
        if session:
            session.version += 1
        await self.db.commit()

        await self.redis.publish(
            f"session:{round_obj.session_id}:events",
            json.dumps({"type": "EVENT", "event": "CODE_SUBMITTED", "payload": {"roundId": round_id}})
        )
