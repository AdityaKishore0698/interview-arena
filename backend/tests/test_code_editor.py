"""The code editor is optional and interviewee-only: when asked to code a
solution, the interviewee (never the interviewer) can run their code against
a DSA problem's sample test cases and submit it, at which point the
interviewer can see it too (persisted, so it's still visible in history
afterward). Execution itself goes through a real third-party API (Piston),
so these tests monkeypatch `code_execution.run_code` to keep them fast and
deterministic — the actual Piston wiring is covered by manual verification,
same pattern as the Google OAuth tests mock their external call."""
import uuid

import pytest
from httpx import AsyncClient

from app.interview import code_execution

pytestmark = pytest.mark.asyncio


async def _matched_pair(client: AsyncClient, problem_title: str | None = None) -> dict:
    suffix = uuid.uuid4().hex[:10]
    email_a, email_b = f"coder_a_{suffix}@example.com", f"coder_b_{suffix}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email_a, "password": "pass", "display_name": "A"})
    await client.post("/api/v1/auth/register", json={"email": email_b, "password": "pass", "display_name": "B"})
    token_a = (await client.post("/api/v1/auth/login", json={"email": email_a, "password": "pass"})).json()["access_token"]
    token_b = (await client.post("/api/v1/auth/login", json={"email": email_b, "password": "pass"})).json()["access_token"]
    id_a = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})).json()["id"]

    rooms = (await client.get("/api/v1/rooms/")).json()["rooms"]
    room_id = next(r["id"] for r in rooms if r["slug"] == "dsa")

    await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_a}"})
    res_b = await client.post("/api/v1/matchmaking/join", json={"room_id": room_id, "mode": "STANDARD"}, headers={"Authorization": f"Bearer {token_b}"})
    session_id = res_b.json()["match"]["match_id"]

    session = (await client.get(f"/api/v1/sessions/{session_id}", headers={"Authorization": f"Bearer {token_a}"})).json()
    round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
    interviewer_id = next(uid for uid, role in round1["roles"].items() if role == "INTERVIEWER")
    token_interviewer = token_a if interviewer_id == id_a else token_b
    token_interviewee = token_b if token_interviewer is token_a else token_a

    if problem_title:
        suggestions = (await client.get(
            f"/api/v1/sessions/{session_id}/rounds/{round1['id']}/problems/suggestions",
            headers={"Authorization": f"Bearer {token_interviewer}"},
        )).json()["problems"]
        chosen = next(p for p in suggestions if p["title"] == problem_title)
        await client.post(
            f"/api/v1/sessions/{session_id}/rounds/{round1['id']}/problem",
            json={"problem_id": chosen["id"]},
            headers={"Authorization": f"Bearer {token_interviewer}"},
        )

    return {
        "token_interviewer": token_interviewer,
        "token_interviewee": token_interviewee,
        "session_id": session_id,
        "round_id": round1["id"],
    }


async def test_only_the_interviewee_can_run_or_submit_code(client: AsyncClient):
    ctx = await _matched_pair(client, problem_title="Two Sum")
    headers = {"Authorization": f"Bearer {ctx['token_interviewer']}"}

    run_res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/run",
        json={"language": "python", "code": "print('hi')"},
        headers=headers,
    )
    assert run_res.status_code == 403

    submit_res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/submit",
        json={"language": "python", "code": "print('hi')"},
        headers=headers,
    )
    assert submit_res.status_code == 403


async def test_submitting_code_persists_and_is_visible_to_both(client: AsyncClient):
    ctx = await _matched_pair(client, problem_title="Two Sum")
    code = "nums = list(map(int, input().split()))\ntarget = int(input())\nprint('0 1')"

    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/submit",
        json={"language": "python", "code": code},
        headers={"Authorization": f"Bearer {ctx['token_interviewee']}"},
    )
    assert res.status_code == 200

    for token in (ctx["token_interviewer"], ctx["token_interviewee"]):
        session = (await client.get(f"/api/v1/sessions/{ctx['session_id']}", headers={"Authorization": f"Bearer {token}"})).json()
        round1 = next(r for r in session["rounds"] if r["round_number"] == 1)
        assert round1["submitted_code"] == code
        assert round1["submitted_language"] == "python"
        assert round1["code_submitted_at"] is not None


async def test_submit_rejects_unsupported_language(client: AsyncClient):
    ctx = await _matched_pair(client, problem_title="Two Sum")
    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/submit",
        json={"language": "cobol", "code": "print"},
        headers={"Authorization": f"Bearer {ctx['token_interviewee']}"},
    )
    assert res.status_code == 400


async def test_run_reports_no_test_cases_for_a_custom_problem(client: AsyncClient):
    ctx = await _matched_pair(client)  # no problem_title -> interviewer never picks; round has no problem yet
    await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/problem",
        json={"custom_text": "Reverse a string, your own way."},
        headers={"Authorization": f"Bearer {ctx['token_interviewer']}"},
    )
    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/run",
        json={"language": "python", "code": "print('x')"},
        headers={"Authorization": f"Bearer {ctx['token_interviewee']}"},
    )
    assert res.status_code == 400


async def test_run_against_real_test_cases_reports_pass_and_fail(client: AsyncClient, monkeypatch):
    ctx = await _matched_pair(client, problem_title="Two Sum")

    async def fake_run_code(language: str, source: str, stdin: str) -> code_execution.ExecutionResult:
        # Mirrors what a correct Two Sum solution would print for the two
        # seeded test cases ("2 7 11 15\n9" -> "0 1", "3 2 4\n6" -> "1 2").
        expected = {"2 7 11 15\n9": "0 1", "3 2 4\n6": "1 2"}
        return code_execution.ExecutionResult(
            stdout=expected.get(stdin, "wrong"), stderr="", exit_code=0, timed_out=False,
        )

    monkeypatch.setattr(code_execution, "run_code", fake_run_code)
    from app.interview import service as service_module
    monkeypatch.setattr(service_module, "code_execution", code_execution)

    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/run",
        json={"language": "python", "code": "whatever — execution is mocked"},
        headers={"Authorization": f"Bearer {ctx['token_interviewee']}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert body["passed_count"] == 2
    assert all(r["passed"] for r in body["results"])


async def test_run_reports_failing_cases_honestly(client: AsyncClient, monkeypatch):
    ctx = await _matched_pair(client, problem_title="Two Sum")

    async def fake_run_code(language: str, source: str, stdin: str) -> code_execution.ExecutionResult:
        return code_execution.ExecutionResult(stdout="9 9", stderr="", exit_code=0, timed_out=False)

    monkeypatch.setattr(code_execution, "run_code", fake_run_code)
    from app.interview import service as service_module
    monkeypatch.setattr(service_module, "code_execution", code_execution)

    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/run",
        json={"language": "python", "code": "print('9 9')"},
        headers={"Authorization": f"Bearer {ctx['token_interviewee']}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["passed_count"] == 0
    assert body["total"] == 2


async def test_run_without_an_execution_api_key_fails_cleanly(client: AsyncClient, monkeypatch):
    """No CODE_EXECUTION_API_KEY configured (the out-of-the-box default) is a
    setup problem, not a 500 crash — run_code raises RuntimeError, which the
    service should turn into a clean 503."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "CODE_EXECUTION_API_KEY", "")

    ctx = await _matched_pair(client, problem_title="Two Sum")
    res = await client.post(
        f"/api/v1/sessions/{ctx['session_id']}/rounds/{ctx['round_id']}/code/run",
        json={"language": "python", "code": "print('hi')"},
        headers={"Authorization": f"Bearer {ctx['token_interviewee']}"},
    )
    assert res.status_code == 503


async def test_languages_endpoint_lists_supported_languages(client: AsyncClient):
    res = await client.get("/api/v1/sessions/code/languages")
    assert res.status_code == 200
    langs = res.json()["languages"]
    for expected in ("python", "javascript", "java", "cpp"):
        assert expected in langs
