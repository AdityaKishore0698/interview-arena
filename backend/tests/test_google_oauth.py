"""Google OAuth is independent of the signup change; these pin its behaviour.

Under TESTING=true (as in the suite) the routes use the built-in mock. The
"real branch" test flips that off and stubs Google's HTTP endpoints so the
actual redirect_uri / token-exchange logic is exercised.
"""
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.identity import router as identity_router

pytestmark = pytest.mark.asyncio


async def test_google_mock_flow_signs_user_in(client: AsyncClient):
    if not identity_router.is_testing:
        pytest.skip("mock OAuth flow only exists under TESTING=true")

    login = await client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert login.status_code in (302, 307)
    assert login.headers["location"] == "/api/v1/auth/google/callback?code=mock_code"

    cb = await client.get(login.headers["location"], follow_redirects=False)
    assert cb.status_code in (302, 307)
    target = urlparse(cb.headers["location"])
    assert f"{target.scheme}://{target.netloc}" == settings.FRONTEND_URL.rstrip("/")
    assert target.path == "/"
    token = parse_qs(target.query)["token"][0]

    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert claims["type"] == "REGISTERED"
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["display_name"] == "Test OAuth User"


async def test_google_real_flow_uses_backend_callback_and_creates_user(client: AsyncClient, monkeypatch):
    backend = "https://api.example.test"
    frontend = "https://app.example.test"
    monkeypatch.setattr(identity_router, "is_testing", False)
    monkeypatch.setattr(settings, "BACKEND_URL", backend)
    monkeypatch.setattr(settings, "FRONTEND_URL", frontend)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "client-secret")

    exchanged: dict = {}

    class _Resp:
        def __init__(self, body):
            self.status_code, self._body = 200, body

        def json(self):
            return self._body

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, data=None, **kw):
            exchanged.update(data)
            return _Resp({"access_token": "google-access"})

        async def get(self, url, headers=None, **kw):
            return _Resp({"email": "google.user@example.com", "name": "Google User"})

    monkeypatch.setattr(identity_router, "httpx", SimpleNamespace(AsyncClient=_FakeClient))

    login = await client.get("/api/v1/auth/google/login", follow_redirects=False)
    redirect_uri = parse_qs(urlparse(login.headers["location"]).query)["redirect_uri"][0]
    assert redirect_uri == f"{backend}/api/v1/auth/google/callback"

    cb = await client.get("/api/v1/auth/google/callback", params={"code": "abc"}, follow_redirects=False)
    assert exchanged["redirect_uri"] == redirect_uri
    assert exchanged["code"] == "abc"
    location = urlparse(cb.headers["location"])
    assert f"{location.scheme}://{location.netloc}" == frontend

    token = parse_qs(location.query)["token"][0]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "google.user@example.com"
