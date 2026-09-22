"""One active session per registered account: signing in again (password or
Google) or logging out invalidates whatever token was issued before it. See
AuthService.issue_session_token and the "sv" claim check in
core/dependencies.get_current_user."""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.identity.models import Profile, User

pytestmark = pytest.mark.asyncio


def _legacy_token(user_id: str) -> str:
    """A token exactly as issued before the "sv" claim existed."""
    payload = {
        "sub": user_id,
        "type": "REGISTERED",
        "exp": datetime.now(UTC) + timedelta(minutes=60),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def test_second_login_invalidates_the_first_token(client: AsyncClient):
    email = f"single_{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "pass", "display_name": "Single"})

    login1 = await client.post("/api/v1/auth/login", json={"email": email, "password": "pass"})
    token1 = login1.json()["access_token"]
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})).status_code == 200

    login2 = await client.post("/api/v1/auth/login", json={"email": email, "password": "pass"})
    token2 = login2.json()["access_token"]
    assert token1 != token2

    stale = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert stale.status_code == 401
    assert "another device" in stale.json()["detail"]

    fresh = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert fresh.status_code == 200


async def test_registration_token_is_invalidated_by_a_later_login(client: AsyncClient):
    email = f"single_{uuid.uuid4()}@example.com"
    reg = await client.post("/api/v1/auth/register", json={"email": email, "password": "pass", "display_name": "Single"})
    reg_token = reg.json()["access_token"]
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {reg_token}"})).status_code == 200

    await client.post("/api/v1/auth/login", json={"email": email, "password": "pass"})

    stale = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {reg_token}"})
    assert stale.status_code == 401


async def test_logout_invalidates_the_token_immediately(client: AsyncClient):
    email = f"single_{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "pass", "display_name": "Single"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert (await client.post("/api/v1/auth/logout", headers=headers)).status_code == 200
    # The token hasn't expired, but logout must still kill it — otherwise
    # logging out is purely a client-side gesture that doesn't actually
    # revoke anything.
    replay = await client.get("/api/v1/auth/me", headers=headers)
    assert replay.status_code == 401


async def test_pre_migration_token_without_sv_claim_still_works(client: AsyncClient, db_session: AsyncSession):
    """A user who hasn't logged in since this feature shipped has
    session_version at its column default (0); their token, minted before
    the "sv" claim existed, must keep working rather than being mass-logged-out."""
    user = User(email=f"legacy_{uuid.uuid4()}@example.com", password_hash=get_password_hash("pass"), is_verified=True)
    user.profile = Profile(display_name="Legacy")
    db_session.add(user)
    await db_session.flush()
    assert user.session_version == 0

    token = _legacy_token(str(user.id))
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200


async def test_guests_are_unaffected_and_can_have_independent_concurrent_sessions(client: AsyncClient):
    guest1 = await client.post("/api/v1/auth/guest")
    guest2 = await client.post("/api/v1/auth/guest")
    token1, token2 = guest1.json()["access_token"], guest2.json()["access_token"]
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})).status_code == 200
