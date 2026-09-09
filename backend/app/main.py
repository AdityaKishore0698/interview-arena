from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.redis import redis_client
from .identity.router import router as auth_router
from .interview.router import router as interview_router
from .matchmaking.router import router as matchmaking_router
from .realtime.router import router as realtime_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
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

import os
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
