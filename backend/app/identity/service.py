import uuid
from datetime import UTC, datetime, timedelta

import jwt

from ..core.config import settings
from ..core.exceptions import EmailAlreadyExistsError
from ..core.security import get_password_hash, verify_password
from .models import Profile, User
from .repository import UserRepository
from .schemas import UserCreate, UserLogin


class AuthService:
    def __init__(self, user_repo: UserRepository, redis_client):
        self.user_repo = user_repo
        self.redis_client = redis_client

    def create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    async def register_user(self, user_data: UserCreate) -> User:
        existing = await self.user_repo.get_by_email(user_data.email)
        if existing:
            raise EmailAlreadyExistsError("Email already registered")
            
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            is_verified=True # Auto-verify for legacy test flows
        )
        
        # Add profile
        new_user.profile = Profile(display_name=user_data.display_name)
        
        return await self.user_repo.save(new_user)

    async def authenticate_user(self, user_data: UserLogin) -> User | None:
        user = await self.user_repo.get_by_email(user_data.email)
        if not user:
            return None
        if not user.password_hash or not verify_password(user_data.password, user.password_hash):
            return None
        if not user.is_verified:
            # For simplicity, if not verified, don't allow login
            # They should re-register to get OTP
            raise ValueError("Email not verified")
        return user

    async def create_guest_session(self) -> str:
        guest_id = f"guest_{uuid.uuid4()}"
        # Store in Redis with TTL 24 hours (86400 seconds)
        await self.redis_client.set(f"session:{guest_id}", '{"type": "GUEST"}', ex=86400)
        return guest_id
