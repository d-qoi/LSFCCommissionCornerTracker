from datetime import datetime
from enum import StrEnum, auto
from pydantic import BaseModel


class PermissionRequestStatus(StrEnum):
    NEW = auto()
    PENDING = auto()
    GRANTED = auto()
    CANCEL = auto()
    DENIED = auto()


class PermissionRequestType(StrEnum):
    CREATE_EVENT = auto()

class PermissionRequestBase(BaseModel):
    username: str
    status: PermissionRequestStatus
    grant_type: PermissionRequestType = PermissionRequestType.CREATE_EVENT

class PermissionRequestInfo(PermissionRequestBase):
    reason: str = ""

class PermissionRequestResponse(PermissionRequestInfo):
    requested_at: datetime
