"""Real server-side formatting for the languages that have a genuine
formatter: Python (black), C/C++ (clang-format), and Java
(google-java-format, mocked here to avoid a real ~200MB JDK download in
CI — its wiring is otherwise identical to the black/clang-format paths,
which run for real). JavaScript/TypeScript are formatted client-side via
Prettier and have no backend endpoint."""
import pytest
from httpx import AsyncClient

from app.interview import code_formatting

pytestmark = pytest.mark.asyncio


async def _authed_headers(client: AsyncClient) -> dict:
    import uuid
    email = f"fmt_{uuid.uuid4().hex[:10]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "pass", "display_name": "F"})
    token = (await client.post("/api/v1/auth/login", json={"email": email, "password": "pass"})).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_format_requires_auth(client: AsyncClient):
    res = await client.post("/api/v1/sessions/code/format", json={"language": "python", "code": "x=1"})
    assert res.status_code == 401


async def test_format_python_with_real_black(client: AsyncClient):
    headers = await _authed_headers(client)
    res = await client.post(
        "/api/v1/sessions/code/format",
        json={"language": "python", "code": "def foo(a,b):\n      return a+b\n"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["formatted_code"] == "def foo(a, b):\n    return a + b\n"


async def test_format_python_syntax_error_is_422(client: AsyncClient):
    headers = await _authed_headers(client)
    res = await client.post(
        "/api/v1/sessions/code/format",
        json={"language": "python", "code": "def foo(:\n"},
        headers=headers,
    )
    assert res.status_code == 422


async def test_format_cpp_with_real_clang_format(client: AsyncClient):
    headers = await _authed_headers(client)
    res = await client.post(
        "/api/v1/sessions/code/format",
        json={"language": "cpp", "code": "int foo(int a,int b){return a+b;}"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["formatted_code"] == "int foo(int a, int b) { return a + b; }"


async def test_format_c_with_real_clang_format(client: AsyncClient):
    headers = await _authed_headers(client)
    res = await client.post(
        "/api/v1/sessions/code/format",
        json={"language": "c", "code": "int foo(int a,int b){return a+b;}"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["formatted_code"] == "int foo(int a, int b) { return a + b; }"


async def test_format_java_wiring(client: AsyncClient, monkeypatch):
    """Mocks the JDK-dependent half only; the endpoint -> format_code ->
    dispatch wiring itself runs for real."""
    def fake_format_java_sync(code: str) -> str:
        return "public class Foo {\n  // formatted\n}\n"

    monkeypatch.setattr(code_formatting, "_format_java_sync", fake_format_java_sync)
    monkeypatch.setitem(code_formatting._FORMATTERS, "java", fake_format_java_sync)

    headers = await _authed_headers(client)
    res = await client.post(
        "/api/v1/sessions/code/format",
        json={"language": "java", "code": "public class Foo{}"},
        headers=headers,
    )
    assert res.status_code == 200
    assert "formatted" in res.json()["formatted_code"]


async def test_format_unsupported_language_is_400(client: AsyncClient):
    headers = await _authed_headers(client)
    res = await client.post(
        "/api/v1/sessions/code/format",
        json={"language": "go", "code": "func foo() {}"},
        headers=headers,
    )
    assert res.status_code == 400
