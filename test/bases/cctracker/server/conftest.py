import logging
from httpx import ASGITransport, AsyncClient
import pytest_asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient

from cctracker.server.core import app
from cctracker.log import get_logger
from cctracker.server.auth import create_dev_token
from cctracker.db.models import Base

aiosqlite_logger = get_logger("aiosqlite")
aiosqlite_logger.setLevel(logging.INFO)



@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite database session for testing"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
def auth_token():
    """Valid dev token with event:create permissions"""
    return create_dev_token("test_user", ["events:create", "admin"])


@pytest.fixture
def auth_headers(auth_token):
    """Authorization headers for API requests"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def httpx_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
