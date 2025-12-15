from datetime import datetime, timedelta, timezone
from typing import Self
from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    HttpUrl,
    PositiveInt,
    field_validator,
    model_validator,
)


class OpenTimes(BaseModel):
    open_time: AwareDatetime
    close_time: AwareDatetime

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.open_time > self.close_time:
            raise ValueError("Open Time after Close Time.")
        elif self.close_time - self.open_time < timedelta(hours=1):
            raise ValueError("Close is under an hour from open.")
        elif self.close_time - self.open_time > timedelta(hours=24):
            raise ValueError("Close is over 24hours from open.")
        return self


class EventDetails(BaseModel):
    name: str
    slug: str
    hostedBy: str
    hostedByUrl: HttpUrl
    startDate: AwareDatetime | None
    endDate: AwareDatetime | None
    seats: PositiveInt = Field(lt=101)
    seatsAvailable: PositiveInt | None
    duration: PositiveInt | None = Field(lt=3600 * 12, default=3600 * 4)
    open: bool
    openTimes: list[OpenTimes] = []


class EventList(BaseModel):
    current: list[EventDetails] = []
    upcoming: list[EventDetails] = []
    past: list[EventDetails] = []


class NewEvent(BaseModel):
    name: str
    slug: str
    hostedBy: str
    hostedByUrl: HttpUrl
    seats: PositiveInt = Field(lt=101)
    duration: PositiveInt = Field(lt=3600 * 12)
    openTimes: list[OpenTimes]

    @field_validator("openTimes")
    @classmethod
    def validate_open_times(cls, v: list[OpenTimes]) -> list[OpenTimes]:
        if not v:
            return v

        sorted_times = sorted(v, key=lambda t: t.open_time)

        # Ensure no overlap
        for prev, curr in zip(sorted_times, sorted_times[1:]):
            if prev.close_time > curr.open_time:
                raise ValueError("Open/close intervals must not overlap")

            if curr.open_time - prev.close_time > timedelta(days=7):
                raise ValueError("Open time can't be a week after last close time.")

        # Only the earliest pair can be on the current day
        today = datetime.now(timezone.utc)

        indices_today: list[int] = []
        for i, ot in enumerate(sorted_times):
            start_date = ot.open_time.astimezone(timezone.utc)
            end_date = ot.close_time.astimezone(timezone.utc)
            if start_date < today < end_date:
                indices_today.append(i)

        if len(indices_today) > 1:
            raise ValueError("Only one open/close pair may be on the current day.")

        return sorted_times
