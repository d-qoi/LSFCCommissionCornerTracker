from enum import StrEnum, auto
from pydantic import BaseModel


class StandardErrorTypes(StrEnum):
    SLUG_EXISTS = auto()
    ADD_TIMES = auto()
    INVALID_START_TIME = auto()
    EVENT_STARTED = auto()
    SEAT_TAKEN = auto()
    INVALID_SEAT = auto()
    ARTIST_NOT_FOUND = auto()
    NO_ACTIVE_SEAT = auto()
    ARTIST_ALREADY_ASSIGNED = auto()
    DWELL_PERIOD = auto()


class StandardError(BaseModel):
    tag: str = "Standard Error"
    code: int
    type: StandardErrorTypes
    details: dict[str, str] = {}
