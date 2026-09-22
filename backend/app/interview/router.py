from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from .repository import RoomRepository

router = APIRouter()

def get_room_repository(db: AsyncSession = Depends(get_db)) -> RoomRepository:
    return RoomRepository(db)

@router.get("/")
async def get_rooms(room_repo: RoomRepository = Depends(get_room_repository)):
    rooms = await room_repo.get_active_rooms()
    return {"rooms": rooms}


from fastapi import HTTPException
from redis.asyncio import Redis

from ..core.redis import get_redis
from .service import SessionService


def get_session_service(db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)):
    return SessionService(db, redis)

from ..core.dependencies import get_current_user


@router.get("/{session_id}")
async def get_session(
    session_id: str, 
    service: SessionService = Depends(get_session_service),
    current_user: dict = Depends(get_current_user)
):
    session = await service.get_session(session_id)
    print("Guest session:", session)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check authorization
    user_id = current_user["id"]
    is_participant = any(p["user_id"] == user_id for p in session["participants"])
    if not is_participant:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    return session


from pydantic import BaseModel


class FeedbackSubmit(BaseModel):
    scores: dict
    comments: str | None = None


class ProblemSelection(BaseModel):
    """Exactly one of these two must be set: pick from the suggested bank,
    or write a question of your own. Picking is optional — a round with
    neither set just keeps today's auto-pick-once-started behavior."""
    problem_id: str | None = None
    custom_text: str | None = None

@router.post("/{session_id}/leave")
async def leave_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
    current_user: dict = Depends(get_current_user)
):
    await service.leave_session(session_id, current_user["id"])
    return {"status": "success"}

@router.post("/{session_id}/rounds/{round_id}/feedback")
async def submit_feedback(
    session_id: str,
    round_id: str,
    feedback: FeedbackSubmit,
    service: SessionService = Depends(get_session_service),
    current_user: dict = Depends(get_current_user)
):
    await service.submit_feedback(session_id, round_id, current_user["id"], feedback.scores, feedback.comments)
    return {"status": "success"}

@router.get("/{session_id}/rounds/{round_id}/problems/suggestions")
async def get_problem_suggestions(
    session_id: str,
    round_id: str,
    service: SessionService = Depends(get_session_service),
    current_user: dict = Depends(get_current_user)
):
    problems = await service.get_problem_suggestions(round_id, current_user["id"])
    return {"problems": problems}

@router.post("/{session_id}/rounds/{round_id}/problem")
async def select_problem(
    session_id: str,
    round_id: str,
    body: ProblemSelection,
    service: SessionService = Depends(get_session_service),
    current_user: dict = Depends(get_current_user)
):
    await service.select_problem(round_id, current_user["id"], body.problem_id, body.custom_text)
    return {"status": "success"}

@router.get("/user/history")
async def get_user_history(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from sqlalchemy import select, desc
    from sqlalchemy.orm import selectinload
    from .models import (
        InterviewSession,
        InterviewParticipant,
        InterviewRound,
        InterviewRoom,
        RoundParticipant,
    )
    import uuid

    user_uuid = uuid.UUID(current_user["id"])
    result = await db.execute(
        select(InterviewSession)
        .join(InterviewParticipant)
        .options(
            selectinload(InterviewSession.rounds)
            .selectinload(InterviewRound.feedbacks),
            selectinload(InterviewSession.rounds)
            .selectinload(InterviewRound.round_participants)
            .selectinload(RoundParticipant.participant),
            selectinload(InterviewSession.participants),
        )
        .where(InterviewParticipant.user_id == user_uuid)
        .where(InterviewSession.status == "COMPLETED")
        .order_by(desc(InterviewSession.created_at))
        .limit(200)
    )
    sessions = result.scalars().unique().all()

    # Resolve room names for the sessions in this page of history.
    room_ids = {s.room_id for s in sessions}
    rooms_by_id = {}
    if room_ids:
        room_rows = (
            await db.execute(select(InterviewRoom).where(InterviewRoom.id.in_(room_ids)))
        ).scalars().all()
        rooms_by_id = {r.id: r for r in room_rows}

    history_data = []
    for s in sessions:
        room = rooms_by_id.get(s.room_id)
        rounds_data = []
        for r in sorted(s.rounds, key=lambda x: x.round_number):
            part_user = {str(rp.participant_id): str(rp.participant.user_id) for rp in r.round_participants}
            feedbacks = []
            for fb in r.feedbacks:
                feedbacks.append({
                    "scores": fb.scores,
                    "comments": fb.comments,
                    "evaluated_role": fb.evaluated_role,
                    "giver_user_id": part_user.get(str(fb.giver_participant_id)),
                    "receiver_user_id": part_user.get(str(fb.receiver_participant_id)),
                })
            rounds_data.append({"round_number": r.round_number, "feedbacks": feedbacks})

        history_data.append({
            "id": str(s.id),
            "mode": s.mode,
            "room": (
                {"name": room.name, "slug": room.slug, "difficulty": room.difficulty}
                if room else None
            ),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "rounds": rounds_data
        })

    return {"history": history_data}
