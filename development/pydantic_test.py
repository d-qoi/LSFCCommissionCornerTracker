from datetime import date, datetime, time, tzinfo
from zoneinfo import ZoneInfo, available_timezones
from pydantic import BaseModel


class TestModel(BaseModel):
    d: date
    dt: datetime
    t: time


tm = TestModel(
    d=date.today(), dt=datetime.now(), t=time(10, tzinfo=ZoneInfo("America/Chicago"))
)
