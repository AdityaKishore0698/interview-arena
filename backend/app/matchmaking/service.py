import asyncio
import logging
import time
import uuid

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..interview.lifecycle import start_session_lifecycle
from ..interview.models import InterviewParticipant, InterviewSession
from .lua_scripts import RESERVE_PAIR_SCRIPT

logger = logging.getLogger(__name__)

class MatchmakingService:
    def __init__(self, redis: Redis, db: AsyncSession):
        self.redis = redis
        self.db = db
        self._reserve_script = self.redis.register_script(RESERVE_PAIR_SCRIPT)
        
    def _get_queue_key(self, room_id: str, mode: str, account_type: str) -> str:
        return f"queue:{room_id}:{mode}:{account_type}"

    async def join_queue(
        self, user_id: str, room_id: str, mode: str, account_type: str, last_partner: str = ""
    ) -> dict | None:

        queue_key = self._get_queue_key(room_id, mode, account_type)
        
        # Prevent queueing if already in an active match
        existing_match = await self.redis.get(f"active_match:{user_id}")
        if existing_match:
            return {"match_id": existing_match.decode() if isinstance(existing_match, bytes) else existing_match, "status": "ALREADY_MATCHED"}
            
        # Remove from old queue if changing modes/rooms
        old_queue = await self.redis.get(f"current_queue:{user_id}")
        if old_queue:
            old_queue_str = old_queue.decode() if isinstance(old_queue, bytes) else old_queue
            if old_queue_str != queue_key:
                await self.redis.zrem(old_queue_str, user_id)
        
        await self.redis.set(f"current_queue:{user_id}", queue_key, ex=900) # 15 min TTL

        lock_prefix = "lock:match:"

        match_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)
        lock_ttl = 10 # seconds
        max_queue_time = 15 * 60 * 1000 # 15 minutes
        
        result = await self._reserve_script(
            keys=[queue_key, lock_prefix],
            args=[user_id, match_id, last_partner, lock_ttl, now_ms, max_queue_time]
        )
        
        if not result:
            return None # Queued, waiting
            
        partner = result[0]
        reserved_match_id = result[1]
        status_flag = result[2]
        
        if status_flag == "LOCKED":
            # I am already locked into a match (e.g. background process matched me)
            # The match_id is reserved_match_id. We just return it. 
            # Note: The partner returned here is actually just myself (user_a), so we don't know the partner yet.
            # We would look it up from the DB or Redis session. For simplicity, just return the match_id.
            return {"match_id": reserved_match_id, "status": "ALREADY_MATCHED"}

        user_b = partner
        
        # Phase 2: Durable Creation
        try:
            if account_type == "GUEST":
                session_key = f"guest_session:{reserved_match_id}"
                await self.redis.hset(session_key, mapping={
                    "user_a": user_id,
                    "user_b": user_b,
                    "room_id": room_id,
                    "mode": mode,
                    "status": "CREATED",
                    "created_at": now_ms
                })
                await self.redis.expire(session_key, 86400)
                asyncio.create_task(start_session_lifecycle(reserved_match_id, is_guest=True))
            else:
                session = InterviewSession(
                    id=uuid.UUID(reserved_match_id),
                    room_id=uuid.UUID(room_id),
                    mode=mode,
                    status="CREATED"
                )
                self.db.add(session)
                await self.db.flush()
                
                part_a = InterviewParticipant(session_id=session.id, user_id=uuid.UUID(user_id), seat=1)
                part_b = InterviewParticipant(session_id=session.id, user_id=uuid.UUID(user_b), seat=2)
                self.db.add_all([part_a, part_b])
                await self.db.flush()
                
                from ..interview.models import InterviewRound, RoundParticipant
                r1 = InterviewRound(session_id=session.id, round_number=1, status="PENDING")
                r2 = InterviewRound(session_id=session.id, round_number=2, status="PENDING")
                self.db.add_all([r1, r2])
                await self.db.flush()
                
                rp1_a = RoundParticipant(round_id=r1.id, participant_id=part_a.id, role="INTERVIEWER")
                rp1_b = RoundParticipant(round_id=r1.id, participant_id=part_b.id, role="INTERVIEWEE")
                
                rp2_a = RoundParticipant(round_id=r2.id, participant_id=part_a.id, role="INTERVIEWEE")
                rp2_b = RoundParticipant(round_id=r2.id, participant_id=part_b.id, role="INTERVIEWER")
                self.db.add_all([rp1_a, rp1_b, rp2_a, rp2_b])
                
                await self.db.commit()
                asyncio.create_task(start_session_lifecycle(str(session.id), is_guest=False))
                
            # Phase 3: Finalization
            await self.redis.delete(f"{lock_prefix}{user_id}", f"{lock_prefix}{user_b}")
            await self.redis.zrem(queue_key, user_id, user_b)
            await self.redis.set(f"active_match:{user_id}", reserved_match_id, ex=86400)
            await self.redis.set(f"active_match:{user_b}", reserved_match_id, ex=86400)
            
            return {
                "match_id": reserved_match_id,
                "user_a": user_id,
                "user_b": user_b,
                "room_id": room_id,
                "mode": mode,
                "status": "NEW_MATCH"
            }
            
        except IntegrityError as e:
            print(f"IntegrityError: {e}")
            await self.db.rollback()
            await self.redis.delete(f"{lock_prefix}{user_id}", f"{lock_prefix}{user_b}")
            await self.redis.zrem(queue_key, user_id, user_b)
            await self.redis.set(f"active_match:{user_id}", reserved_match_id, ex=86400)
            await self.redis.set(f"active_match:{user_b}", reserved_match_id, ex=86400)
            return {
                "match_id": reserved_match_id,
                "user_a": user_id,
                "user_b": user_b,
                "room_id": room_id,
                "mode": mode,
                "status": "RECOVERED_MATCH"
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create session {reserved_match_id} in DB: {e}")
            raise
            raise

    async def leave_queue(self, user_id: str, room_id: str, mode: str, account_type: str) -> None:
        queue_key = self._get_queue_key(room_id, mode, account_type)
        await self.redis.zrem(queue_key, user_id)
        # We don't remove locks here, if they are locked, they are locked until TTL.

    async def get_status(self, user_id: str) -> dict | None:
        match_id = await self.redis.get(f"active_match:{user_id}")
        if match_id:
            return {"status": "MATCH_FOUND", "match_id": match_id}
        return {"status": "QUEUED"}
