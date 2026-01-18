from enum import StrEnum, auto
from fastapi import HTTPException, status
from valkey.asyncio import Valkey

from cctracker.log import get_logger

_log = get_logger(__name__)

_client: Valkey | None = None

class ArtistSeatStatus(StrEnum):
    pending = auto()
    pending_creation = auto()
    active = auto()
    inactive = auto()


def setup_valkey(conn_string: str) -> Valkey:
    global _client

    if _client:
        _log.debug(
            "Valkey connection pool already initialized, returning existing instance"
        )
        return _client

    _client = Valkey.from_url(conn_string)

    return _client


def with_vk() -> Valkey:
    if _client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database Connection Error: Cucumber",
        )

    return _client
