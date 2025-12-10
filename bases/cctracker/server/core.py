from cctracker.server.config import config
from cctracker.log import get_logger, configure_logging

configure_logging(config.log_level, config.log_file)

from fastapi import FastAPI

from cctracker.server.auth import api_router as auth_router

log = get_logger(__name__)

app = FastAPI()

app.include_router(auth_router)
