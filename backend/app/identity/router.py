import os
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..core.exceptions import (
    AccountDisabledError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from ..core.redis import get_redis
from .repository import UserRepository
from .schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GuestAuthResponse,
    ResetPasswordRequest,
    Token,
    UpdateProfileRequest,
    UserCreate,
    UserLogin,
)
from .service import RESET_CODE_TTL_SECONDS, AuthService

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
    """Create the account immediately and sign the user in.

    No email verification / OTP: the response carries the same JWT that
    /login would issue, so the client can go straight into the app.
    """
    try:
        user = await auth_service.register_user(user_data)
        await db.commit()
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except IntegrityError:
        # Two concurrent signups for the same email: the unique constraint won.
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

    access_token = auth_service.create_access_token({"sub": str(user.id), "type": "REGISTERED"})
    return {"user_id": str(user.id), "access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin, 
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        user = await auth_service.authenticate_user(user_data)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except AccountDisabledError as e:
        raise HTTPException(status_code=403, detail=str(e))
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


@router.patch("/me")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user["type"] != "REGISTERED":
        raise HTTPException(status_code=403, detail="Guests have no profile to update")
    display_name = body.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Display name cannot be empty")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(current_user["id"]))
    if not user or not user.profile:
        raise HTTPException(status_code=404, detail="User not found")
    user.profile.display_name = display_name
    await db.commit()
    return {"status": "success", "display_name": display_name}


@router.post("/password/change", status_code=status.HTTP_200_OK)
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    if current_user["type"] != "REGISTERED":
        raise HTTPException(status_code=403, detail="Guests cannot change a password")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    user = await auth_service.user_repo.get_by_id(uuid.UUID(current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        await auth_service.change_password(user, body.current_password, body.new_password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    return {"status": "success"}


@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_account(
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    if current_user["type"] != "REGISTERED":
        raise HTTPException(status_code=403, detail="Guest sessions expire on their own — nothing to delete")

    user = await auth_service.user_repo.get_by_id(uuid.UUID(current_user["id"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await auth_service.delete_account(user)
    await db.commit()

    user_id = current_user["id"]
    await redis.delete(f"active_match:{user_id}")
    await redis.delete(f"current_queue:{user_id}")
    return {"status": "success"}


# --- OAUTH & PASSWORD RESET ---


@router.get("/google/login")
async def google_login():
    if is_testing:
        return RedirectResponse(url="/api/v1/auth/google/callback?code=mock_code")

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/google/callback"
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
        redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/google/callback"
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
        from .models import Profile, User

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


@router.post("/password/forgot", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """DEMO password recovery — no email is sent.

    The reset code is returned in the response so the UI can show it directly.
    This is intentionally not production-grade recovery: anyone who knows an
    account's email can obtain a code for it.
    """
    code = await auth_service.request_password_reset(body.email)
    if code is None:
        # Unknown / non-resettable account: hand back an equally-shaped decoy
        # (never stored, so it can't be redeemed) so the response doesn't
        # reveal which emails are registered.
        code = auth_service.generate_reset_code()
    return {
        "status": "demo",
        "demo_code": code,
        "expires_in": RESET_CODE_TTL_SECONDS,
        "notice": "DEMO recovery: no email is sent. Use this code on the reset screen.",
    }


@router.post("/password/reset", status_code=status.HTTP_200_OK)
async def reset_password(
    body: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
):
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    try:
        await auth_service.reset_password(body.email, body.otp, body.new_password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return {"status": "success"}
