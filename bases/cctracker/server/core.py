import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from cctracker.server.config import config
from cctracker.server.api.auth import api_router as auth_router
from cctracker.server.api.events import api_router as event_router
from cctracker.server.api.artist import api_router as artist_router
from cctracker.server.api.event_artist import api_router as ea_router
from cctracker.log import get_logger
from cctracker.fs import setup_minio
from cctracker.cache import setup_valkey
from cctracker.db import setup_db, models

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    if config.dev_db:
        aiosqlite_logger = get_logger("aiosqlite")
        aiosqlite_logger.setLevel(logging.INFO)
        db_engine = setup_db("sqlite+aiosqlite:///cctracker_dev.db")
    else:
        db_engine = setup_db(str(config.db_conn_string))

    async with db_engine.begin() as conn:
        log.info("Configuring Database")
        await conn.run_sync(models.Base.metadata.create_all)

    _minio_client = setup_minio(
        config.minio_url,
        config.minio_access_key,
        config.minio_secret_key,
        bucket=config.minio_bucket,
    )
    valkey_client = setup_valkey(config.valkey_url)

    yield

    log.info("Returning from server, finishing lifespan")

    await db_engine.dispose()
    await valkey_client.aclose()

    log.info("Goodbye")


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(event_router)
app.include_router(artist_router)
app.include_router(ea_router)
