import random
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from ..core.config import settings
from ..core.exceptions import (
    AccountDisabledError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from ..core.security import get_password_hash, verify_password
from .models import Profile, User
from .repository import UserRepository
from .schemas import UserCreate, UserLogin

RESET_CODE_TTL_SECONDS = 900


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
            # Email verification is intentionally not part of signup; the
            # column is kept (no schema change) and always set for new users.
            is_verified=True,
        )
        
        # Add profile
        new_user.profile = Profile(display_name=user_data.display_name)
        
        return await self.user_repo.save(new_user)

    async def authenticate_user(self, user_data: UserLogin) -> User | None:
        user = await self.user_repo.get_by_email(user_data.email)
        if not user:
            return None
        if user.status != "ACTIVE":
            raise AccountDisabledError("This account has been deleted")
        if not user.password_hash or not verify_password(user_data.password, user.password_hash):
            return None
        # No `is_verified` gate: email verification no longer exists, and
        # accounts created before the column was added default to false with
        # no way to ever verify them — gating on it would lock them out.
        return user

    async def create_guest_session(self) -> str:
        guest_id = f"guest_{uuid.uuid4()}"
        # Store in Redis with TTL 24 hours (86400 seconds)
        await self.redis_client.set(f"session:{guest_id}", '{"type": "GUEST"}', ex=86400)
        return guest_id

    async def request_password_reset(self, email: str) -> str | None:
        """Generate and store a reset code. Returns the code, or None if the
        account can't receive one (unknown or deleted account) — the caller
        must still respond in the same shape, to avoid leaking which emails
        are registered."""
        user = await self.user_repo.get_by_email(email)
        if not user or user.status != "ACTIVE":
            return None
        code = self.generate_reset_code()
        await self.redis_client.setex(f"pwreset:{email}", RESET_CODE_TTL_SECONDS, code)
        return code

    @staticmethod
    def generate_reset_code() -> str:
        return str(random.randint(100000, 999999))

    async def reset_password(self, email: str, otp: str, new_password: str) -> None:
        stored = await self.redis_client.get(f"pwreset:{email}")
        if not stored or stored != otp:
            raise InvalidCredentialsError("Invalid or expired code")
        user = await self.user_repo.get_by_email(email)
        if not user or user.status != "ACTIVE":
            raise InvalidCredentialsError("Invalid or expired code")
        user.password_hash = get_password_hash(new_password)
        await self.redis_client.delete(f"pwreset:{email}")

    async def change_password(self, user: User, current_password: str | None, new_password: str) -> None:
        if user.password_hash and (not current_password or not verify_password(current_password, user.password_hash)):
            raise InvalidCredentialsError("Current password is incorrect")
        # OAuth-only accounts (no password_hash yet) may set an initial password.
        user.password_hash = get_password_hash(new_password)

    async def delete_account(self, user: User) -> None:
        """Soft-delete: interview history/feedback referencing this user must
        survive (FKs have no cascade), so we deactivate + anonymize instead of
        removing the row."""
        user.status = "DELETED"
        user.email = f"deleted-{user.id}@deleted.invalid"
        user.password_hash = None
        if user.profile:
            user.profile.display_name = "Deleted User"
