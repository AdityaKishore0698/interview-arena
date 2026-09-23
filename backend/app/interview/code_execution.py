"""Thin client for Judge0 CE via RapidAPI, the sandboxed third-party code
execution service used for "Run" (DSA rounds only — see
SessionService.run_code_against_tests). Judge0 runs a full program against
raw stdin and returns raw stdout; there's no per-language function-stub
harness, which is why DSA problems carry an `io_note` describing their
input/output convention instead.

Needs a RapidAPI key: sign up at rapidapi.com, subscribe to the free Judge0
CE tier (https://rapidapi.com/judge0-official/api/judge0-ce), and set
CODE_EXECUTION_API_KEY in .env. Without a key, Run fails with a clear 502
rather than a confusing one — see the check in run_code below.
"""
from dataclasses import dataclass
from typing import Any

import httpx

from ..core.config import settings

# language id (as offered in the editor's picker) -> (Judge0 language_id, human label)
SUPPORTED_LANGUAGES: dict[str, tuple[int, str]] = {
    "python": (100, "Python (3.12.5)"),
    "javascript": (102, "JavaScript (Node.js 22.08.0)"),
    "typescript": (101, "TypeScript (5.6.2)"),
    "java": (91, "Java (JDK 17.0.6)"),
    "cpp": (105, "C++ (GCC 14.1.0)"),
    "c": (103, "C (GCC 14.1.0)"),
    "csharp": (51, "C# (Mono 6.6.0.161)"),
    "go": (107, "Go (1.23.5)"),
    "ruby": (72, "Ruby (2.7.0)"),
}

_CPU_TIME_LIMIT_SECONDS = 5

# Judge0 status ids: https://ce.judge0.com/statuses
_STATUS_ACCEPTED = 3
_STATUS_TIME_LIMIT_EXCEEDED = 5
_STATUS_COMPILATION_ERROR = 6


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool


async def run_code(language: str, source: str, stdin: str) -> ExecutionResult:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    if not settings.CODE_EXECUTION_API_KEY:
        raise RuntimeError(
            "CODE_EXECUTION_API_KEY is not set — sign up for the free Judge0 CE "
            "tier on RapidAPI and set it in .env to enable Run."
        )
    language_id, _label = SUPPORTED_LANGUAGES[language]

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{settings.CODE_EXECUTION_API_URL}/submissions",
            params={"base64_encoded": "false", "wait": "true"},
            headers={
                "X-RapidAPI-Key": settings.CODE_EXECUTION_API_KEY,
                "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
                "Content-Type": "application/json",
            },
            json={
                "source_code": source,
                "language_id": language_id,
                "stdin": stdin,
                "cpu_time_limit": _CPU_TIME_LIMIT_SECONDS,
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()

    status_id = (data.get("status") or {}).get("id")
    status_description = (data.get("status") or {}).get("description") or "Unknown error"

    if status_id == _STATUS_COMPILATION_ERROR:
        return ExecutionResult(
            stdout="", stderr=data.get("compile_output") or "Compilation failed",
            exit_code=None, timed_out=False,
        )

    stdout = data.get("stdout") or ""
    stderr = data.get("stderr") or ""
    if status_id != _STATUS_ACCEPTED and not stderr:
        stderr = status_description

    return ExecutionResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=data.get("exit_code"),
        timed_out=status_id == _STATUS_TIME_LIMIT_EXCEEDED,
    )
