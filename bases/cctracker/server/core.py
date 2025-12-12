from cctracker.server.config import config
from cctracker.log import get_logger, configure_logging

configure_logging(config.log_level, config.log_file)

from contextlib import asynccontextmanager

from fastapi import FastAPI

from cctracker.server.auth import api_router as auth_router
from cctracker.fs import setup_minio
from cctracker.cache import setup_valkey
from cctracker.db import setup_db, models

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
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

    await db_engine.dispose()
    await valkey_client.aclose()


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
