import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .models import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(select(User).options(selectinload(User.profile)).where(User.email == email))
        return result.scalars().first()
        
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(select(User).options(selectinload(User.profile)).where(User.id == user_id))
        return result.scalars().first()

    async def save(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user
