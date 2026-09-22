import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..identity.repository import UserRepository
from .config import settings
from .database import get_db
from .redis import get_redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = str(payload.get("sub")) if payload.get("sub") else None
        user_type = str(payload.get("type")) if payload.get("type") else None
        if user_id is None or user_type is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    if user_type == "GUEST":
        session_data = await redis.get(f"session:{user_id}")
        if not session_data:
            raise HTTPException(status_code=401, detail="Guest session expired")
        return {"id": user_id, "type": "GUEST"}
        
    elif user_type == "REGISTERED":
        user_repo = UserRepository(db)
        try:
            parsed_id = uuid.UUID(user_id)
        except ValueError:
            raise credentials_exception
        user = await user_repo.get_by_id(parsed_id)
        if not user or user.status != "ACTIVE":
            raise credentials_exception
        # A token with no "sv" claim predates this check and is treated as
        # version 0 — matching a never-logged-in-since user's column default,
        # so it keeps working until their next login. See
        # AuthService.issue_session_token for where "sv" is set and bumped.
        if payload.get("sv", 0) != user.session_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Logged out: this account was signed in from another device",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "id": str(user.id),
            "type": "REGISTERED",
            "display_name": user.profile.display_name if user.profile else "User",
            "email": user.email,
            "avatar_url": user.profile.avatar_url if user.profile else None,
        }

    raise credentials_exception
