from enum import StrEnum, auto
from pydantic import BaseModel

class StandardErrorTypes(StrEnum):
    SLUG_EXISTS = auto()
    ADD_TIMES = auto()
    INVALID_START_TIME = auto()
    EVENT_STARTED = auto()

class StandardError(BaseModel):
    code: int
    type: StandardErrorTypes
    details: dict[str, str] = {}
