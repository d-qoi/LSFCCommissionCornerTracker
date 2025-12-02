from datetime import timedelta
from enum import StrEnum, auto
from pydantic import AwareDatetime, BaseModel

from fastapi.security import OAuth2AuthorizationCodeBearer

scopes: dict[str, str] = {
    "event:create": "Create an event, and delete created event",
    "event:admin": "Create events, and delete any create events",
    "user:me": "Access User Profile, only theirs",
    "user:admin": "Access any user profile",
}

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    "authorizationUrl", "tokenURL", scopes=scopes
)


class EventManagementDetails(BaseModel):
    name: str | None = None
    slug: str | None = None
    open_close_times: list[list[AwareDatetime]] = []
    manual_open: bool = False
    manual_close: bool = False
    spotss: int | None = None
    spots_time: timedelta | None = None


class Spot(BaseModel):
    artist_id: str | None
    spot: int


class SpotList(BaseModel):
    spotss: list[Spot] = []


class EventStatus(StrEnum):
    UPCOMMING = auto()
    OPEN = auto()
    CLOSED = auto()
    PAST = auto()


class EventDetails(BaseModel):
    status: EventStatus = EventStatus.UPCOMMING
    next_time: AwareDatetime | None = None
    seats: int | None = None
    artists: list[str] | None = None
    time_till_seat_available: timedelta | None = None
