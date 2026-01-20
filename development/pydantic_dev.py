from datetime import date, datetime, time, timedelta, tzinfo, timezone
from enum import StrEnum, auto
from zoneinfo import ZoneInfo, available_timezones
from pydantic import BaseModel

from cctracker.models.events import NewEvent, OpenTimes



class TestModel(BaseModel):
    d: date
    dt: datetime
    t: time


tm = TestModel(
    d=date.today(), dt=datetime.now(), t=time(10, tzinfo=ZoneInfo("America/New_York"))
)

now = datetime.now(ZoneInfo("America/New_York"))

new_event = NewEvent(
    name="TestEvent",
    slug="test-event2",
    hostedBy="https://example.com",
    hostedByUrl="https://example.com",
    seats=10,
    duration=3600*4,
    openTimes=[
        OpenTimes(open_time=now + timedelta(days=0, minutes=-60), close_time=now+timedelta(minutes=3)),
        OpenTimes(open_time=now + timedelta(days=2), close_time=now+timedelta(days=2,hours=8)),
        OpenTimes(open_time=now + timedelta(days=3), close_time=now+timedelta(days=3,hours=8)),
        OpenTimes(open_time=now + timedelta(days=4), close_time=now+timedelta(days=4,hours=8)),
    ]
)

class TestEnum(StrEnum):
    t1 = auto()
    t2 = auto()

class TestModel2(BaseModel):
    t1: TestEnum
