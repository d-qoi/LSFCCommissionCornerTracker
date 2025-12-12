from enum import StrEnum, auto
from pydantic import BaseModel

class StandardErrorTypes(StrEnum):
    SLUG_EXISTS = auto()
    INVALID_START_TIME = auto()

class StandardError(BaseModel):
    code: int
    type: StandardErrorTypes
    details: dict[str, str] = {}
