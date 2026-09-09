from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import uuid
import random

from ..core.config import settings
from ..core.database import get_db
from ..core.exceptions import EmailAlreadyExistsError
from ..core.redis import get_redis
from .repository import UserRepository
from .schemas import GuestAuthResponse, Token, UserCreate, UserLogin
from .service import AuthService
from ..core.dependencies import get_current_user
import os

is_testing = os.environ.get("TESTING", "").lower() == "true"

router = APIRouter()


def get_auth_service(
    db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)
) -> AuthService:
    user_repo = UserRepository(db)
    return AuthService(user_repo, redis)


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.register_user(user_data)
        await db.commit()
        return {"user_id": str(user.id)}
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin, 
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        user = await auth_service.authenticate_user(user_data)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
        
    access_token = auth_service.create_access_token({"sub": str(user.id), "type": "REGISTERED"})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post(
    "/guest", response_model=GuestAuthResponse, status_code=status.HTTP_201_CREATED
)
async def create_guest(auth_service: AuthService = Depends(get_auth_service)):
    guest_id = await auth_service.create_guest_session()
    access_token = auth_service.create_access_token({"sub": guest_id, "type": "GUEST"})
    return {"access_token": access_token, "token_type": "bearer", "guest_id": guest_id}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: dict = Depends(get_current_user), redis: Redis = Depends(get_redis)
):
    user_id = current_user["id"]
    await redis.delete(f"active_match:{user_id}")
    await redis.delete(f"current_queue:{user_id}")
    return {"status": "success"}


# --- OAUTH & OTP ---


@router.get("/google/login")
async def google_login():
    if is_testing:
        return RedirectResponse(url="/api/v1/auth/google/callback?code=mock_code")

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    redirect_uri = f"{settings.FRONTEND_URL}/api/v1/auth/google/callback"
    url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}&scope=openid%20email%20profile&access_type=offline"
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    email = ""
    name = ""

    if is_testing and code == "mock_code":
        # Mock user for E2E
        email = f"test_oauth_{uuid.uuid4().hex[:8]}@example.com"
        name = "Test OAuth User"
    else:
        redirect_uri = f"{settings.FRONTEND_URL}/api/v1/auth/google/callback"
        token_url = "https://oauth2.googleapis.com/token"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code")
            access_token = resp.json().get("access_token")

            user_info = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_info.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch user info")

            user_data = user_info.json()
            email = user_data.get("email")
            name = user_data.get("name")

    if not email:
        raise HTTPException(status_code=400, detail="No email from Google")

    # Find or create user
    user = await auth_service.user_repo.get_by_email(email)
    if not user:
        from .models import User, Profile

        user = User(
            email=email, auth_provider="google", is_verified=True, password_hash=None
        )
        user.profile = Profile(display_name=name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # If user exists, mark as verified if it was unverified
        if not user.is_verified:
            user.is_verified = True
            await db.commit()

    access_token = auth_service.create_access_token(
        {"sub": str(user.id), "type": "REGISTERED"}
    )
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/?token={access_token}"
    )


class OTPRequest(UserCreate):
    pass  # we can reuse it, or just make a simple schema


class OTPSend(UserCreate):
    pass


@router.post("/otp/send")
async def send_otp(
    data: dict,  # email, password, name
    redis: Redis = Depends(get_redis),
):
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    otp = "123456" if is_testing else str(random.randint(100000, 999999))

    # In production, send via SES/SendGrid. For now, print.
    print(f"OTP for {email}: {otp}")

    await redis.setex(f"otp:{email}", 300, otp)
    # Store pending registration data temporarily
    await redis.setex(f"pending_reg:{email}", 300, json.dumps(data))

    return {"status": "sent"}


import json


@router.post("/otp/verify")
async def verify_otp(
    data: dict,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP required")

    stored_otp = await redis.get(f"otp:{email}")
    if not stored_otp or stored_otp != otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    pending = await redis.get(f"pending_reg:{email}")
    if not pending:
        raise HTTPException(status_code=400, detail="Registration data expired")

    reg_data = json.loads(pending)

    user = await auth_service.user_repo.get_by_email(email)
    if user:
        if user.is_verified:
            raise HTTPException(
                status_code=409, detail="User already registered and verified"
            )
        else:
            user.is_verified = True
            await db.commit()
    else:
        # Create user
        from .schemas import UserCreate

        try:
            uc = UserCreate(**reg_data)
            user = await auth_service.register_user(uc)
            user.is_verified = True
            await db.commit()
        except EmailAlreadyExistsError:
            raise HTTPException(status_code=409, detail="Email exists")

    await redis.delete(f"otp:{email}")
    await redis.delete(f"pending_reg:{email}")

    access_token = auth_service.create_access_token(
        {"sub": str(user.id), "type": "REGISTERED"}
    )
    return {"access_token": access_token, "token_type": "bearer"}
