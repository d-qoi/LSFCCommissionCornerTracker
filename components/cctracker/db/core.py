from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from cctracker.log import get_logger

_log = get_logger(__name__)

_engine: AsyncEngine | None = None
_sessionMaker: async_sessionmaker[AsyncSession] | None = None

def setup_db(conn_string: str) -> AsyncEngine:
    global _engine
    global _sessionMaker

    if _engine:
        _log.debug("DB is already set up, returning existing instance of engine")
        return _engine

    _log.debug("Setting Up DB Connection")

    _engine = create_async_engine(conn_string)
    _sessionMaker = async_sessionmaker(_engine, expire_on_commit=False, autoflush=False)

    _log.debug("DB Connection Success")

    return _engine


async def with_db():
    _log.debug("with_db called")

    if _sessionMaker is None or _engine is None:
        raise HTTPException(status_code=500, detail="Database Connection Error: apple")
    async with _sessionMaker() as db:
        try:
            yield db
            await db.flush()
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            await db.close()
