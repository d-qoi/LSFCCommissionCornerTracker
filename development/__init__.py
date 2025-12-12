import datetime

from datetime import timezone, tzinfo
from zoneinfo import ZoneInfo


def between(a: int):
    return 1 < a < 5


def between_dates(when: datetime.date):
    return datetime.date(1995,1,1) < when < datetime.date(2030,1,1)

def between_datetime(when: datetime.datetime):
    start = datetime.datetime.now(ZoneInfo("America/Chicago")) - datetime.timedelta(days=1000)
    end = datetime.datetime.now(ZoneInfo("America/Chicago")) + datetime.timedelta(days=1000)

    return start < when < end
