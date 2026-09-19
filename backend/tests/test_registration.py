"""Email/password signup is a single step: the account exists and the caller
is signed in as soon as /register returns. No OTP, no email, no verification."""
import importlib.util
import smtplib
import uuid
from unittest.mock import patch

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.identity.models import Profile, User

pytestmark = pytest.mark.asyncio


def _payload(**overrides) -> dict:
    body = {
        "email": f"signup_{uuid.uuid4().hex[:10]}@example.com",
        "password": "correct-horse-battery",
        "display_name": "New Person",
    }
    body.update(overrides)
    return body


async def test_signup_creates_user_immediately(client: AsyncClient, db_session: AsyncSession):
    body = _payload()
    res = await client.post("/api/v1/auth/register", json=body)
    assert res.status_code == 201

    user = (await db_session.execute(select(User).where(User.email == body["email"]))).scalar_one()
    assert str(user.id) == res.json()["user_id"]
    assert user.status == "ACTIVE"
    assert user.is_verified is True
    assert user.auth_provider == "local"
    profile = (await db_session.execute(select(Profile).where(Profile.user_id == user.id))).scalar_one()
    assert profile.display_name == "New Person"


async def test_signup_hashes_password(client: AsyncClient, db_session: AsyncSession):
    body = _payload()
    await client.post("/api/v1/auth/register", json=body)
    user = (await db_session.execute(select(User).where(User.email == body["email"]))).scalar_one()
    assert user.password_hash and user.password_hash != body["password"]
    assert user.password_hash.startswith("$2")  # bcrypt


async def test_signup_returns_usable_jwt(client: AsyncClient):
    body = _payload()
    res = await client.post("/api/v1/auth/register", json=body)
    data = res.json()
    assert data["token_type"] == "bearer"

    claims = jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert claims["sub"] == data["user_id"]
    assert claims["type"] == "REGISTERED"

    # The returned token authenticates straight away — no login round-trip.
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == body["email"]
    assert me.json()["display_name"] == "New Person"


async def test_signup_generates_no_otp(client: AsyncClient, redis):
    body = _payload()
    res = await client.post("/api/v1/auth/register", json=body)
    assert res.status_code == 201
    assert await redis.keys("otp:*") == []
    assert await redis.keys("pending_reg:*") == []
    assert await redis.keys("pwreset:*") == []
    # Nothing at all should be left behind in Redis by a signup.
    assert await redis.keys("*") == []


async def test_signup_sends_no_email(client: AsyncClient):
    with (
        patch.object(smtplib, "SMTP", side_effect=AssertionError("SMTP must not be used at signup")),
        patch.object(smtplib, "SMTP_SSL", side_effect=AssertionError("SMTP must not be used at signup")),
    ):
        res = await client.post("/api/v1/auth/register", json=_payload())
    assert res.status_code == 201
    # There is no email module to call any more.
    assert importlib.util.find_spec("app.core.email") is None


@pytest.mark.parametrize("path", ["/api/v1/auth/otp/send", "/api/v1/auth/otp/verify"])
async def test_otp_endpoints_are_gone(client: AsyncClient, path: str):
    res = await client.post(path, json={"email": "a@example.com", "otp": "123456"})
    assert res.status_code == 404


async def test_login_works_after_signup(client: AsyncClient):
    body = _payload()
    await client.post("/api/v1/auth/register", json=body)
    login = await client.post(
        "/api/v1/auth/login", json={"email": body["email"], "password": body["password"]}
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"

    wrong = await client.post(
        "/api/v1/auth/login", json={"email": body["email"], "password": "not-the-password"}
    )
    assert wrong.status_code == 401


async def test_legacy_unverified_user_can_still_log_in(client: AsyncClient, db_session: AsyncSession):
    """Accounts created before verification was removed may have is_verified=False
    (the column was added with a false default and never backfilled). They must
    not be locked out."""
    email = f"legacy_{uuid.uuid4().hex[:8]}@example.com"
    user = User(email=email, password_hash=get_password_hash("legacy-password"), is_verified=False)
    user.profile = Profile(display_name="Legacy")
    db_session.add(user)
    await db_session.flush()

    res = await client.post("/api/v1/auth/login", json={"email": email, "password": "legacy-password"})
    assert res.status_code == 200


async def test_duplicate_email_rejected(client: AsyncClient):
    body = _payload()
    assert (await client.post("/api/v1/auth/register", json=body)).status_code == 201
    dup = await client.post("/api/v1/auth/register", json={**body, "display_name": "Someone Else"})
    assert dup.status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "not-an-email"},
        {"password": ""},
        {"password": "   "},
        {"password": "é" * 37},  # 74 UTF-8 bytes: over bcrypt's 72-byte limit
        {"display_name": ""},
        {"display_name": "   "},
        {"display_name": "x" * 101},
    ],
)
async def test_invalid_signup_is_rejected_without_creating_user(
    client: AsyncClient, db_session: AsyncSession, overrides: dict
):
    body = _payload(**overrides)
    res = await client.post("/api/v1/auth/register", json=body)
    assert res.status_code == 422
    found = (await db_session.execute(select(User).where(User.email == body["email"]))).scalar_one_or_none()
    assert found is None


async def test_max_length_inputs_are_accepted(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json=_payload(password="a" * 72, display_name="n" * 100),
    )
    assert res.status_code == 201
