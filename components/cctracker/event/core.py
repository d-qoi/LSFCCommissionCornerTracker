from datetime import timedelta
from enum import StrEnum, auto
from pydantic import AwareDatetime, BaseModel

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
