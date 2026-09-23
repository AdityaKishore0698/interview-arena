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


async def test_forgot_password_unknown_email_gets_unredeemable_decoy(client: AsyncClient, redis):
    # Same response shape as a real account, so registration can't be probed,
    # but the code is never stored and can't be used.
    email = "nobody-here@example.com"
    res = await client.post("/api/v1/auth/password/forgot", json={"email": email})
    assert res.status_code == 200
    data = res.json()
    assert data["demo_code"].isdigit() and len(data["demo_code"]) == 6
    assert await redis.get(f"pwreset:{email}") is None

    reset = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": email, "otp": data["demo_code"], "new_password": "newpassword123"},
    )
    assert reset.status_code == 400


async def test_forgot_password_returns_demo_code_and_stores_it_with_expiry(client: AsyncClient, redis):
    email, _password, _token = await _register_and_login(client)

    res = await client.post("/api/v1/auth/password/forgot", json={"email": email})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "demo"
    assert "DEMO" in data["notice"]
    assert data["expires_in"] == 900
    assert set(data) == {"status", "demo_code", "expires_in", "notice"}  # nothing else leaks

    # The returned code is the one stored server-side, with the same expiry.
    assert await redis.get(f"pwreset:{email}") == data["demo_code"]
    ttl = await redis.ttl(f"pwreset:{email}")
    assert 0 < ttl <= 900


async def test_forgot_and_reset_password_flow(client: AsyncClient, redis):
    email, password, _token = await _register_and_login(client)

    res = await client.post("/api/v1/auth/password/forgot", json={"email": email})
    assert res.status_code == 200
    code = res.json()["demo_code"]

    # Wrong code is rejected (and the real code survives a bad guess)
    bad = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": email, "otp": "000000" if code != "000000" else "111111", "new_password": "newpassword123"},
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

    # The code is single-use
    replay = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": email, "otp": code, "new_password": "anotherpass123"},
    )
    assert replay.status_code == 400


async def test_expired_reset_code_is_rejected(client: AsyncClient, redis):
    email, password, _token = await _register_and_login(client)
    code = (await client.post("/api/v1/auth/password/forgot", json={"email": email})).json()["demo_code"]

    await redis.delete(f"pwreset:{email}")  # what Redis does when the TTL lapses

    res = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": email, "otp": code, "new_password": "newpassword123"},
    )
    assert res.status_code == 400
    # Password unchanged
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200


async def test_reset_enforces_minimum_password_length(client: AsyncClient):
    email, _password, _token = await _register_and_login(client)
    code = (await client.post("/api/v1/auth/password/forgot", json={"email": email})).json()["demo_code"]
    res = await client.post(
        "/api/v1/auth/password/reset",
        json={"email": email, "otp": code, "new_password": "short"},
    )
    assert res.status_code == 400


async def test_password_recovery_needs_no_email_or_smtp(client: AsyncClient):
    import importlib.util
    import smtplib
    from unittest.mock import patch

    from app.core.config import settings

    # The email module and SMTP settings no longer exist at all.
    assert importlib.util.find_spec("app.core.email") is None
    assert not [name for name in vars(settings) if name.startswith("SMTP_")]

    email, _password, _token = await _register_and_login(client)
    with (
        patch.object(smtplib, "SMTP", side_effect=AssertionError("SMTP must not be used")),
        patch.object(smtplib, "SMTP_SSL", side_effect=AssertionError("SMTP must not be used")),
    ):
        res = await client.post("/api/v1/auth/password/forgot", json={"email": email})
    assert res.status_code == 200


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


async def test_update_avatar_data_uri(client: AsyncClient):
    _email, _password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    data_uri = "data:image/jpeg;base64," + ("A" * 100)

    res = await client.patch("/api/v1/auth/me", json={"display_name": "N", "avatar_url": data_uri}, headers=headers)
    assert res.status_code == 200
    assert res.json()["avatar_url"] == data_uri

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["avatar_url"] == data_uri


async def test_update_avatar_https_url(client: AsyncClient):
    _email, _password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.patch(
        "/api/v1/auth/me", json={"display_name": "N", "avatar_url": "https://example.com/me.png"}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["avatar_url"] == "https://example.com/me.png"


async def test_avatar_rejects_non_image_scheme(client: AsyncClient):
    _email, _password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.patch(
        "/api/v1/auth/me", json={"display_name": "N", "avatar_url": "javascript:alert(1)"}, headers=headers
    )
    assert res.status_code == 400


async def test_avatar_rejects_oversized_payload(client: AsyncClient):
    _email, _password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    huge = "data:image/jpeg;base64," + ("A" * 400_000)
    res = await client.patch("/api/v1/auth/me", json={"display_name": "N", "avatar_url": huge}, headers=headers)
    assert res.status_code == 400


async def test_avatar_can_be_removed(client: AsyncClient):
    _email, _password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/auth/me", json={"display_name": "N", "avatar_url": "https://example.com/a.png"}, headers=headers)

    res = await client.patch("/api/v1/auth/me", json={"display_name": "N", "avatar_url": ""}, headers=headers)
    assert res.status_code == 200
    assert res.json()["avatar_url"] is None


async def test_avatar_untouched_when_field_omitted(client: AsyncClient):
    _email, _password, token = await _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.patch("/api/v1/auth/me", json={"display_name": "N", "avatar_url": "https://example.com/a.png"}, headers=headers)

    res = await client.patch("/api/v1/auth/me", json={"display_name": "N2"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["avatar_url"] == "https://example.com/a.png"


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
