from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..core.redis import get_redis
from .service import MatchmakingService

router = APIRouter()

class JoinQueueRequest(BaseModel):
    room_id: str
    mode: str = "STANDARD"
    last_partner: str = ""

def get_matchmaking_service(redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_db)):
    return MatchmakingService(redis, db)

@router.post("/join", status_code=status.HTTP_200_OK)
async def join_queue(
    req: JoinQueueRequest,
    current_user: dict = Depends(get_current_user),
    service: MatchmakingService = Depends(get_matchmaking_service)
):
    if req.mode not in ["QUICK", "STANDARD"]:
        raise HTTPException(status_code=400, detail="Invalid mode")
        
    match = await service.join_queue(
        user_id=current_user["id"],
        room_id=req.room_id,
        mode=req.mode,
        account_type=current_user["type"],
        last_partner=req.last_partner
    )
    
    if match:
        status = match.get("status", "MATCH_FOUND")
        if status == "ALREADY_MATCHED":
            return {"status": "ALREADY_MATCHED", "match": match}
        return {"status": "MATCH_FOUND", "match": match}
    else:
        return {"status": "QUEUED"}

@router.post("/leave", status_code=status.HTTP_200_OK)
async def leave_queue(
    req: JoinQueueRequest,
    current_user: dict = Depends(get_current_user),
    service: MatchmakingService = Depends(get_matchmaking_service)
):
    await service.leave_queue(
        user_id=current_user["id"],
        room_id=req.room_id,
        mode=req.mode,
        account_type=current_user["type"]
    )
    return {"status": "CANCELED"}

@router.get("/status", status_code=status.HTTP_200_OK)
async def get_status(
    current_user: dict = Depends(get_current_user),
    service: MatchmakingService = Depends(get_matchmaking_service)
):
    result = await service.get_status(current_user["id"])
    return result
