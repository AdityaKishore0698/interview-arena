import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app

test_engine = create_async_engine(settings.DATABASE_URL, echo=False)

@pytest.fixture
async def db_session():
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        
        async_session_maker = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint"
        )
        async with async_session_maker() as session:
            yield session
            
        await transaction.rollback()

@pytest.fixture(autouse=True)
async def flush_redis():
    from app.core.redis import get_redis
    r = await get_redis()
    await r.flushdb()
    yield
    await r.flushdb()

@pytest.fixture
async def client(db_session: AsyncSession):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


from app.core.redis import get_redis


@pytest.fixture
async def redis():
    r = await get_redis()
    yield r
