from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status, Response, Security
from sqlalchemy import select, exists, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cctracker.db import with_db, models
from cctracker.log import get_logger
from cctracker.models.artists import ArtistSummary
from cctracker.models.events import EventDetails, EventList, NewEvent, OpenTimes
from cctracker.models.errors import StandardError, StandardErrorTypes
from cctracker.server.helpers import CurrentUser, with_event


_log = get_logger(__name__)

api_router = APIRouter(prefix="/event", tags=["event operations"])


@api_router.get("/list")
async def get_all_events(db: Annotated[AsyncSession, Depends(with_db)]) -> EventList:
    """Get all events"""

    _log.info("Fetching all events")

    event_list = EventList()

    stmt = select(models.Event).options(
        selectinload(models.Event.open_times),
        selectinload(models.Event.seats).selectinload(models.Seat.assignments),
        selectinload(models.Event.artists),
        selectinload(models.Event.assignments)
    )
    _log.debug("Executing database query for all events")
    results = await db.scalars(stmt)

    today = datetime.now(ZoneInfo("UTC"))
    for result in results:
        event = EventDetails(
            name=result.name,
            slug=result.slug,
            hostedBy=result.hostedBy,
            hostedByUrl=result.hostedByUrl,
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
    _log.info(f"Retrieved {len(event_list.upcoming)} upcoming, ")
    _log.info(
        f"{len(event_list.current)} current, and {len(event_list.past)} past events"
    )
    return event_list


@api_router.post("/create")
async def create_event(
    newEventDetails: NewEvent,
    response: Response,
    _user: Annotated[
        models.UserData | None, Security(CurrentUser, scopes=["event:create"])
    ],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> StandardError | EventDetails:
    _log.info(
        f"User attempting to create event: '{newEventDetails.name}' with slug '{newEventDetails.slug}'"
    )

    exists_stmt = select(exists().where(models.Event.slug == newEventDetails.slug))
    slug_exists = await db.scalar(exists_stmt)

    if bool(slug_exists):
        _log.warning(
            f"Event creation failed: slug '{newEventDetails.slug}' already exists"
        )
        response.status_code = status.HTTP_409_CONFLICT
        return StandardError(
            code=status.HTTP_409_CONFLICT,
            type=StandardErrorTypes.SLUG_EXISTS,
        )

    _log.debug("Slug does not exist, continuing")

    new_event = models.Event(
        slug=newEventDetails.slug,
        name=newEventDetails.name,
        # TODO: Replace this with an actual username
        createdBy="temp",
        hostedBy=newEventDetails.hostedBy,
        hostedByUrl=str(newEventDetails.hostedByUrl),
        seatDuration=newEventDetails.duration,
    )

    _log.debug(f"New Event: {new_event}")

    if len(newEventDetails.openTimes) == 0:
        _log.warning(
            f"Event creation failed: no open times specified for '{newEventDetails.name}'"
        )
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
    _log.debug(
        f"Creating event with {newEventDetails.seats} seats and {len(newEventDetails.openTimes)} time slots"
    )

    db.add(new_event)
    await db.commit()
    _log.info(
        f"Successfully created event '{new_event.name}' with slug '{new_event.slug}'"
    )

    response.status_code = status.HTTP_201_CREATED
    return EventDetails(
        name=new_event.name,
        slug=new_event.slug,
        hostedBy=new_event.hostedBy,
        hostedByUrl=new_event.hostedByUrl,
        startDate=new_event.event_start,
        endDate=new_event.event_end,
        seats=new_event.seat_count,
        seatsAvailable=new_event.seat_count,
        open=new_event.event_open,
        duration=new_event.seatDuration,
    )


@api_router.get("/{eventId}")
async def get_event(
    eventId: str,
    event: Annotated[models.Event, Depends(with_event)],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> EventDetails:

    _log.debug(f"Fetching details for event '{eventId}'")

    openTimes:list[OpenTimes] = []

    for time in event.open_times:
        openTimes.append(OpenTimes(
            open_time=time.open_time,
            close_time=time.close_time
            ))

    event_details = EventDetails(
        name=event.name,
        slug=event.slug,
        hostedBy=event.hostedBy,
        hostedByUrl=event.hostedByUrl,
        startDate=event.event_start,
        endDate=event.event_end,
        seats=event.seat_count,
        seatsAvailable=event.seats_available,
        open=event.event_open,
        openTimes=openTimes,
        duration=event.seatDuration,
    )

    _log.debug(f"Event '{eventId}': {event.seats_available}/{event.seat_count} seats available, ")
    _log.debug(f"open={event.event_open}")

    return event_details


@api_router.get("/{eventId}/artists")
async def get_event_artists(
    eventId: str,
    all: bool,
    event: Annotated[models.Event, Depends(with_event)],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> list[ArtistSummary]:
    _log.debug(f"Fetching artists for event '{eventId}' (include_unseated={all})")

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

    _log.info(
        f"Event '{eventId}': returning {len(artist_list)} seated artists"
        + (f" and {len(unseated_artists)} unseated artists" if unseated_artists else "")
    )
    artist_list += unseated_artists

    return artist_list


# Update this to check who has permissions to update the event.
@api_router.post("/{eventId}")
async def update_event(
    eventId: str,
    updatedEvent: NewEvent,
    response: Response,
    event: Annotated[models.Event, Depends(with_event)],
    _user: Annotated[
        models.UserData | None, Security(CurrentUser, scopes=["event:create"])
    ],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> EventDetails | StandardError:
    """
    Update an existing event, changing only the fields provided in the NewEvent structure.
    Identified by slug in the path (eventId).
    """

    _log.info(f"User attempting to update event '{eventId}'")

    if event.event_open:
        _log.warning(f"Update denied: event '{eventId}' is currently running")
        response.status_code = status.HTTP_403_FORBIDDEN
        return StandardError(
            code=status.HTTP_403_FORBIDDEN, type=StandardErrorTypes.EVENT_STARTED
        )

    elif updatedEvent.slug != event.slug:
        _log.debug(f"Event slug changing from '{event.slug}' to '{updatedEvent.slug}'")
        exists_stmt = select(exists().where(models.Event.slug == updatedEvent.slug))
        slug_taken = await db.scalar(exists_stmt)

        if slug_taken:
            _log.warning(
                f"Update failed: new slug '{updatedEvent.slug}' already exists"
            )
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
        _log.info(
            f"Updating seat count for '{eventId}': {current_seat_count} -> {desired_seat_count}"
        )
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
        hostedByUrl=event.hostedByUrl,
        startDate=event.event_start,
        endDate=event.event_end,
        seats=event.seat_count,
        seatsAvailable=event.seat_count,
        open=event.event_open,
        duration=event.seatDuration,
        openTimes=[OpenTimes(open_time=t.open_time, close_time=t.close_time) for t in event.open_times]
    )

    _log.info(f"Successfully updated event '{eventId}' (new slug: '{updated.slug}')")
    return updated


# TODO: update this to check user who created the event
@api_router.delete("/{eventId}")
async def delete_event(
    eventId: str,
    event: Annotated[models.Event, Depends(with_event)],
    _user: Annotated[
        models.UserData | None, Security(CurrentUser, scopes=["admin", "event:create"])
    ],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """Delete an event, Admin only"""
    _log.info(f"User attempting to delete event '{eventId}'")

    await db.delete(event)
    await db.commit()

    _log.info(f"Successfully deleted event '{eventId}'")
