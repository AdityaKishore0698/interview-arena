import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient) -> tuple[str, str, str]:
    email = f"acct_{uuid.uuid4()}@example.com"
    password = "originalpass123"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Original Name"},
    )
    assert reg.status_code == 201
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return email, password, token


async def test_forgot_password_unknown_email_does_not_error(client: AsyncClient):
    # Must not leak whether the email is registered.
    res = await client.post("/api/v1/auth/password/forgot", json={"email": "nobody-here@example.com"})
    assert res.status_code == 200
    assert res.json()["status"] == "sent"


async def test_forgot_and_reset_password_flow(client: AsyncClient, redis):
    email, password, _token = await _register_and_login(client)

    res = await client.post("/api/v1/auth/password/forgot", json={"email": email})
    assert res.status_code == 200

    code = await redis.get(f"pwreset:{email}")
    assert code is not None

    # Wrong code is rejected
    bad = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": email, "otp": "000000", "new_password": "newpassword123"},
    )
    assert bad.status_code == 400

    # Correct code resets the password
    ok = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": email, "otp": code, "new_password": "newpassword123"},
    )
    assert ok.status_code == 200

    # Old password no longer works, new one does
    old_login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert old_login.status_code == 401
    new_login = await client.post("/api/v1/auth/login", json={"email": email, "password": "newpassword123"})
    assert new_login.status_code == 200


async def test_change_password_requires_current_password(client: AsyncClient):
    _email, password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    wrong = await client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "not-it", "new_password": "brandnewpass123"},
        headers=headers,
    )
    assert wrong.status_code == 403

    ok = await client.post(
        "/api/v1/auth/password/change",
        json={"current_password": password, "new_password": "brandnewpass123"},
        headers=headers,
    )
    assert ok.status_code == 200


async def test_update_profile_display_name(client: AsyncClient):
    _email, _password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.patch("/api/v1/auth/me", json={"display_name": "New Name"}, headers=headers)
    assert res.status_code == 200

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["display_name"] == "New Name"


async def test_guest_cannot_update_profile_or_password(client: AsyncClient):
    guest = await client.post("/api/v1/auth/guest")
    headers = {"Authorization": f"Bearer {guest.json()['access_token']}"}

    res = await client.patch("/api/v1/auth/me", json={"display_name": "X"}, headers=headers)
    assert res.status_code == 403

    res2 = await client.post(
        "/api/v1/auth/password/change",
        json={"new_password": "whatever123"},
        headers=headers,
    )
    assert res2.status_code == 403


async def test_delete_account_revokes_access_and_blocks_login(client: AsyncClient):
    email, password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.delete("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200

    # The old token is now invalid.
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 401

    # The (now-anonymized) account cannot log in with the original email either.
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code in (401, 403)
