from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .models import InterviewRoom


class RoomRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_rooms(self) -> list[InterviewRoom]:
        result = await self.db.execute(select(InterviewRoom).where(InterviewRoom.is_active == True))
        return list(result.scalars().all())
