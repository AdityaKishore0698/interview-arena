import asyncio
import uuid

import pytest

from app.matchmaking.service import MatchmakingService

pytestmark = pytest.mark.asyncio

async def test_matchmaking_concurrency(redis, db_session):
    service = MatchmakingService(redis, db_session)
    room_id = str(uuid.uuid4())
    user_ids = [str(uuid.uuid4()) for _ in range(10)]
    
    tasks = []
    for u in user_ids:
        tasks.append(service.join_queue(u, room_id, "STANDARD", "GUEST"))
        
    results = await asyncio.gather(*tasks)
    
    matches = [r for r in results if r is not None]
    matched_users = set()
    for m in matches:
        if m.get("status") == "NEW_MATCH":
            matched_users.add(m["user_a"])
            matched_users.add(m["user_b"])
        
    assert len(matched_users) > 0

async def test_matchmaking_failure_recovery(redis, db_session):
    service = MatchmakingService(redis, db_session)
    room_id = str(uuid.uuid4())
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    
    class BadDB:
        def add(self, obj): pass
        def add_all(self, objs): pass
        async def flush(self): pass
        async def commit(self): raise Exception("DB Failure")
        async def rollback(self): pass
        
    bad_service = MatchmakingService(redis, BadDB())
    
    await bad_service.join_queue(user_a, room_id, "QUICK", "REGISTERED")
    
    with pytest.raises(Exception, match="DB Failure"):
        await bad_service.join_queue(user_b, room_id, "QUICK", "REGISTERED")
        
    queue_key = f"queue:{room_id}:QUICK:REGISTERED"
    score_a = await redis.zscore(queue_key, user_a)
    assert score_a is not None
    score_b = await redis.zscore(queue_key, user_b)
    assert score_b is not None
    
    lock_a = await redis.get(f"lock:match:{user_a}")
    assert lock_a is not None
