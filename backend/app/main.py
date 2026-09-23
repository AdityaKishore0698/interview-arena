import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.redis import redis_client
from .identity.router import router as auth_router
from .interview.router import router as interview_router
from .matchmaking.router import router as matchmaking_router
from .realtime.router import router as realtime_router

logger = logging.getLogger(__name__)


async def _prewarm_java_formatter() -> None:
    """The Java code-formatting path needs a real JDK, which is downloaded
    and cached on first use (see app/interview/code_formatting.py) — that
    first download takes ~30s. Kicking it off here, in the background, at
    startup means a fresh deploy is ready before the first real user hits
    it, instead of making them wait. Best-effort: a failure here (e.g. no
    network yet) just means the lazy download happens on first use instead.
    """
    from .interview.code_formatting import _java_binary_path
    try:
        await asyncio.to_thread(_java_binary_path)
        logger.info("Java formatter pre-warmed")
    except Exception as e:
        logger.warning(f"Java formatter pre-warm failed, will retry lazily on first use: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if os.environ.get("TESTING", "").lower() != "true":
        asyncio.create_task(_prewarm_java_formatter())
    yield
    # Shutdown
    await redis_client.aclose()

app = FastAPI(title="Interview Arena API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(interview_router, prefix="/api/v1/rooms", tags=["rooms"])
app.include_router(interview_router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(matchmaking_router, prefix="/api/v1/matchmaking", tags=["matchmaking"])
app.include_router(realtime_router, prefix="/api/v1", tags=["realtime"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}

from .core.redis import get_redis
from fastapi import Depends
from redis.asyncio import Redis

def _require_test_mode():
    if os.environ.get("TESTING", "").lower() != "true":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only available in test mode")


@app.post("/api/v1/debug/flush-redis")
async def debug_flush_redis(redis: Redis = Depends(get_redis)):
    """Test-only endpoint. Only operational when TESTING=true. Flushes all Redis keys."""
    _require_test_mode()
    await redis.flushdb()
    return {"status": "flushed"}


@app.delete("/api/v1/debug/redis")
async def debug_delete_redis(redis: Redis = Depends(get_redis)):
    """Test-only alias used by the Playwright E2E suite to reset Redis between specs."""
    _require_test_mode()
    await redis.flushdb()
    return {"status": "flushed"}
