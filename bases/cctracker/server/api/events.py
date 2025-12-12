from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import HttpUrl
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cctracker.db import with_db, models
from cctracker.log import get_logger
from cctracker.models.events import EventDetails, EventList, NewEvent
from cctracker.models.errors import StandardError, StandardErrorTypes

_log = get_logger(__name__)

api_router = APIRouter(prefix="/event")


@api_router.get("/list")
async def get_all_events(db: Annotated[AsyncSession, Depends(with_db)]) -> EventList:
    """Get all events"""

    _log.info("get_all_events called")

    event_list = EventList()

    stmt = select(models.Event).options(
        selectinload(models.Event.open_times),
        selectinload(models.Event.seats),
    )
    results = await db.scalars(stmt)

    today = datetime.now(ZoneInfo("UTC"))
    for result in results:
        event = EventDetails(
            name=result.name,
            slug=result.slug,
            hostedBy=result.hostedBy,
            hostedByURL=HttpUrl(result.hostedByUrl),
            startDate=result.event_start,
            endDate=result.event_end,
            seats=result.seat_count,
            seatsAvailable=result.seats_available,
            open=result.event_open,
        )

        _log.debug(f"Event: {event}")

        if event.startDate is None or event.endDate is None:
            _log.warning(
                f"Start and end date not defined for {event.name} - {event.slug}"
            )
            event_list.upcoming.append(event)
            continue

        assert event.startDate is not None
        assert event.endDate is not None

        if event.startDate.date() > today.date():
            _log.debug("Start date > today")
            event_list.upcoming.append(event)

        elif event.endDate.date() < today.date():
            _log.debug("End date < today")
            event_list.past.append(event)

        else:
            _log.debug("Current Event")
            event_list.current.append(event)
    _log.debug(f"Upcoming: {len(event_list.upcoming)}")
    _log.debug(f"Current: {len(event_list.current)}")
    _log.debug(f"Past: {len(event_list.past)}")
    _log.debug("get_all_events finished")
    return event_list


@api_router.get("/{eventId}")
async def get_event(
    eventId: str, db: Annotated[AsyncSession, Depends(with_db)]
) -> EventDetails:

    _log.info(f"get_event/{eventId} called")
    stmt = (
        select(models.Event)
        .where(models.Event.slug == eventId)
        .options(
            selectinload(models.Event.open_times),
            selectinload(models.Event.seats),
        )
    )
    result = await db.scalar(stmt)

    if result is None:
        _log.debug(f"Event {eventId} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{eventId} not found"
        )

    event = EventDetails(
        name=result.name,
        slug=result.slug,
        hostedBy=result.hostedBy,
        hostedByURL=result.hostedByUrl,
        startDate=result.event_start,
        endDate=result.event_end,
        seats=result.seat_count,
        seatsAvailable=result.seats_available,
        open=result.event_open,
    )

    _log.debug(f"get_event/{eventId} finished")

    return event


@api_router.post("/create")
async def create_event(
    newEventDetails: NewEvent,
    response: Response,
    db: Annotated[AsyncSession, Depends(with_db)],
):
    _log.info(f"Creating a new event: {newEventDetails.name}")
    exists_stmt = select(exists().where(models.Event.slug == newEventDetails.slug))
    slug_exists = await db.scalar(exists_stmt)

    if bool(slug_exists):
        response.status_code = status.HTTP_409_CONFLICT
        return StandardError(
            code=status.HTTP_409_CONFLICT,
            type=StandardErrorTypes.SLUG_EXISTS,
        )

    new_event = models.Event(
        slug=newEventDetails.slug,
        name=newEventDetails.name,
        hostedBy=newEventDetails.hostedBy,
        hostedByUrl=newEventDetails.hostedByUrl,
    )

    for timePairs in newEventDetails.openTimes:
        new_event.open_times.append(
            models.OpenTime(
                open_time=timePairs.open_time, close_time=timePairs.close_time
            )
        )

    new_event.seats = [
        models.Seat(seat_number=i) for i in range(1, newEventDetails.seats + 1)
    ]

    db.add(new_event)
    await db.commit()

    response.status_code = status.HTTP_201_CREATED
    return EventDetails(
        name=new_event.name,
        slug=new_event.slug,
        hostedBy=new_event.hostedBy,
        hostedByURL=new_event.hostedByUrl,
        startDate=new_event.event_start,
        endDate=new_event.event_end,
        seats=new_event.seat_count,
        seatsAvailable=new_event.seats_available,
        open=new_event.event_open,
    )
