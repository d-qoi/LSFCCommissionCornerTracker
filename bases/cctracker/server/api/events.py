from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status, Response, Security
from sqlalchemy import select, exists, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cctracker.db import with_db, models
from cctracker.log import get_logger
from cctracker.models import artists
from cctracker.models.artists import ArtistSummary
from cctracker.models.events import EventDetails, EventList, NewEvent
from cctracker.models.errors import StandardError, StandardErrorTypes
from cctracker.server.helpers import get_event
from cctracker.server.auth import get_current_user

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
            hostedByURL=result.hostedByUrl,
            startDate=result.event_start,
            endDate=result.event_end,
            seats=result.seat_count,
            seatsAvailable=result.seats_available,
            open=result.event_open,
            duration=result.seatDuration,
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


@api_router.post("/create")
async def create_event(
    newEventDetails: NewEvent,
    response: Response,
    _user: Annotated[
        dict[str, str], Security(get_current_user, scopes="events:create")
    ],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> StandardError | EventDetails:
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
        # TODO: Replace this with an actual username
        createdBy="temp",
        hostedBy=newEventDetails.hostedBy,
        hostedByUrl=str(newEventDetails.hostedByUrl),
        duration=newEventDetails.duration,
    )

    if len(newEventDetails.openTimes) == 0:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return StandardError(
            code=status.HTTP_400_BAD_REQUEST, type=StandardErrorTypes.ADD_TIMES
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
        duration=new_event.seatDuration,
    )


@api_router.get("/{eventId}")
async def get_event(
    eventId: str,
    event: Annotated[models.Event, Depends(get_event)],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> EventDetails:

    _log.info(f"get_event/{eventId} called")

    event_details = EventDetails(
        name=event.name,
        slug=event.slug,
        hostedBy=event.hostedBy,
        hostedByURL=event.hostedByUrl,
        startDate=event.event_start,
        endDate=event.event_end,
        seats=event.seat_count,
        seatsAvailable=event.seats_available,
        open=event.event_open,
        duration=event.seatDuration,
    )

    _log.debug(f"get_event/{eventId} finished")

    return event_details


@api_router.get("/{eventId}/artists")
async def get_event_artists(
    eventId: str, all: bool,
    event: Annotated[models.Event, Depends(get_event)],
    db: Annotated[AsyncSession, Depends(with_db)]
) -> list[ArtistSummary]:
    _log.debug(f"{eventId}/artists called")

    artist_list: list[ArtistSummary] = []
    unseated_artists: list[ArtistSummary] = []
    for artist in event.artists:
        seat = artist.current_seat
        if seat is None:
            if all:
                unseated_artists.append(
                    ArtistSummary(
                        name=artist.name,
                        slug=artist.slug,
                        eventId=eventId,
                        imageUrl=artist.imageUrl,
                        seat=0,
                    )
                )
            continue

        artist_list.append(
            ArtistSummary(
                name=artist.name,
                slug=artist.slug,
                eventId=eventId,
                imageUrl=artist.imageUrl,
                seat=seat.seat_number,
            )
        )

    _log.debug(f"{len(artist_list)} artists seated, {len(unseated_artists)} not seated")
    artist_list += unseated_artists

    return artist_list


# Update this to check who has permissions to update the event.
@api_router.post("/{eventId}")
async def update_event(
    eventId: str,
    updatedEvent: NewEvent,
    response: Response,
    event: Annotated[models.Event, Depends(get_event)],
    _user: Annotated[
        dict[str, str], Security(get_current_user, scopes=["events:create"])
    ],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> EventDetails | StandardError:
    """
    Update an existing event, changing only the fields provided in the NewEvent structure.
    Identified by slug in the path (eventId).
    """

    _log.info(f"Updating event {eventId}")

    if event.event_open:
        _log.debug(f"Event {eventId} is running")
        response.status_code = status.HTTP_403_FORBIDDEN
        return StandardError(
            code=status.HTTP_403_FORBIDDEN, type=StandardErrorTypes.EVENT_STARTED
        )

    elif updatedEvent.slug != event.slug:
        exists_stmt = select(exists().where(models.Event.slug == updatedEvent.slug))
        slug_taken = await db.scalar(exists_stmt)

        if slug_taken:
            response.status_code = status.HTTP_409_CONFLICT
            return StandardError(
                code=status.HTTP_409_CONFLICT, type=StandardErrorTypes.SLUG_EXISTS
            )

    event.slug = updatedEvent.slug
    event.name = updatedEvent.name
    event.hostedBy = updatedEvent.hostedBy
    event.hostedByUrl = str(updatedEvent.hostedByUrl)
    event.seatDuration = updatedEvent.duration

    event.open_times.clear()
    for timePairs in updatedEvent.openTimes:
        event.open_times.append(
            models.OpenTime(
                open_time=timePairs.open_time,
                close_time=timePairs.close_time,
            )
        )

    current_seat_count = len(event.seats)
    desired_seat_count = updatedEvent.seats

    if desired_seat_count != current_seat_count:
        # Simple approach: drop all and recreate
        # (If you need to preserve assignments, you can swap this for smarter logic)
        event.seats.clear()
        event.seats = [
            models.Seat(seat_number=i) for i in range(1, desired_seat_count + 1)
        ]

    await db.commit()
    await db.refresh(event)

    updated = EventDetails(
        name=event.name,
        slug=event.slug,
        hostedBy=event.hostedBy,
        hostedByURL=event.hostedByUrl,
        startDate=event.event_start,
        endDate=event.event_end,
        seats=event.seat_count,
        seatsAvailable=event.seats_available,
        open=event.event_open,
        duration=event.seatDuration,
    )

    _log.debug(f"update_event/{eventId} finished: {updated.slug}")
    return updated


# TODO: update this to check user who created the event
@api_router.delete("/{eventId}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    eventId: str,
    _user: Annotated[
        dict[str, str], Security(get_current_user, scopes=["admin", "event:create"])
    ],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """Delete an event, Admin only"""
    stmt = (
        delete(models.Event)
        .where(models.Event.slug == eventId)
        .returning(models.Event.name)
    )
    result = await db.execute(stmt)
    event_name = result.scalar()
    if event_name is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{eventId} not found",
        )

    _log.info(f"Deleted {event_name} at {eventId}")

    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
