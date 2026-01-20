from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, status, Response, Security
from pydantic import BaseModel
from sqlalchemy import select, exists, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from valkey.asyncio import Valkey

from cctracker.cache.core import with_vk
from cctracker.db import with_db, models
from cctracker.log import get_logger
from cctracker.models.artists import ArtistSummary
from cctracker.models.events import EventDetails, EventList, NewEvent, OpenTimes
from cctracker.models.errors import StandardError, StandardErrorTypes
from cctracker.server.auth import CurrentPrincipal, Principal
from cctracker.server.helpers import CurrentUser, with_event, require_event_editor
from cctracker.server.seat_expiration_helper import expire_stale_seats


_log = get_logger(__name__)

api_router = APIRouter(prefix="/event", tags=["event operations"])


@api_router.get("/list")
async def get_all_events(db: Annotated[AsyncSession, Depends(with_db)],
                         vk: Annotated[Valkey, Depends(with_vk)]) -> EventList:
    """Get all events"""

    _log.info("Fetching all events")

    event_list = EventList()

    stmt = select(models.Event).options(
        selectinload(models.Event.open_times),
        selectinload(models.Event.seats).selectinload(models.Seat.assignments),
        selectinload(models.Event.artists),
        selectinload(models.Event.assignments),
    )
    _log.debug("Executing database query for all events")
    results = await db.scalars(stmt)

    today = datetime.now(ZoneInfo("UTC"))
    for result in results:
        await expire_stale_seats(result, db, vk)
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
    user: Annotated[
        models.UserData, Security(CurrentUser, scopes=["event:create"])
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
        createdBy=user.username,
        hostedBy=newEventDetails.hostedBy,
        hostedByUrl=str(newEventDetails.hostedByUrl),
        seatDuration=newEventDetails.duration,
        dwellPeriod=newEventDetails.dwellPeriod,
        owner_user_id=user.id,
    )

    new_event.editors.append(user)

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


@api_router.get("/{eventId}", dependencies=[Depends(expire_stale_seats)])
async def get_event(
    eventId: str,
    event: Annotated[models.Event, Depends(with_event)],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> EventDetails:

    _log.debug(f"Fetching details for event '{eventId}'")

    openTimes: list[OpenTimes] = []

    for time in event.open_times:
        openTimes.append(
            OpenTimes(open_time=time.open_time, close_time=time.close_time)
        )

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

    _log.debug(
        f"Event '{eventId}': {event.seats_available}/{event.seat_count} seats available, "
    )
    _log.debug(f"open={event.event_open}")

    return event_details


@api_router.get("/{eventId}/artists", dependencies=[Depends(expire_stale_seats)])
async def get_event_artists(
    eventId: str,
    all: bool,
    event: Annotated[models.Event, Depends(with_event)],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> list[ArtistSummary]:
    """
    Returns a list of all artists associated with the event.
    """
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
@api_router.post("/{eventId}", dependencies=[Depends(expire_stale_seats)])
async def update_event(
    eventId: str,
    updatedEvent: NewEvent,
    response: Response,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user: Annotated[
        models.UserData | None, Depends(CurrentUser)
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
        openTimes=[
            OpenTimes(open_time=t.open_time, close_time=t.close_time)
            for t in event.open_times
        ],
    )

    _log.info(f"Successfully updated event '{eventId}' (new slug: '{updated.slug}')")
    return updated


@api_router.delete("/{eventId}")
async def delete_event(
    eventId: str,
    event: Annotated[models.Event, Depends(with_event)],
    user: Annotated[
        models.UserData, Security(CurrentUser, scopes=["admin", "event:create"])
    ],
    principal: Annotated[Principal, Depends(CurrentPrincipal)],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """Delete an event, Admin only"""
    _log.info(f"User: {user.username} is attempting to delete event '{eventId}'")
    _log.debug(f"scopes for user: {principal.scopes}")
    _log.debug(f"Event owner: {event.owner.username}")

    if "admin" in principal.scopes or user.username == event.owner.username:
        await db.delete(event)
        await db.commit()
        _log.info(f"Successfully deleted event '{eventId}'")
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Only event owners or admins can delete an event",
    )


class Editor(BaseModel):
    username: str


@api_router.post("/{eventId}/editors", dependencies=[Depends(expire_stale_seats)])
async def add_event_editor(
    eventId: str,
    editor: Editor,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """Add an editor to the event"""
    _log.info(
        f"User {user.username} adding editor {editor.username} to event {eventId}"
    )

    stmt = select(models.UserData).where(models.UserData.username == editor.username)
    target_user = await db.scalar(stmt)

    if not target_user:
        _log.warning(
            f"User {editor.username} not found when adding as editor to {eventId}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {editor.username} not found",
        )

    if target_user in event.editors:
        _log.warning(f"{editor.username} is already an editor of {eventId}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{editor.username} is already an editor",
        )

    event.editors.append(target_user)
    await db.commit()

    _log.info(f"Added {editor.username} as editor to {eventId}")


@api_router.delete(
    "/{eventId}/editors/{username}", dependencies=[Depends(expire_stale_seats)]
)
async def remove_event_editor(
    eventId: str,
    editor: Editor,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """Remove an editor from the event"""
    username = editor.username
    _log.info(f"User {user.username} removing editor {username} from event {eventId}")

    if event.owner.username is not user.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Only the event owner can delete an event",
        )

    stmt = select(models.UserData).where(models.UserData.username == username)
    target_user = await db.scalar(stmt)

    if not target_user:
        _log.warning(
            f"User {username} not found when removing as editor from {eventId}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {username} not found"
        )

    if target_user not in event.editors:
        _log.warning(f"{username} is not an editor of {eventId}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{username} is not an editor"
        )

    event.editors.remove(target_user)
    await db.commit()

    _log.info(f"Removed {username} as editor from {eventId}")


@api_router.get("/{eventId}/editors", dependencies=[Depends(expire_stale_seats)])
async def list_event_editors(
    eventId: str,
    event: Annotated[models.Event, Depends(with_event)],
) -> list[Editor]:
    """List all editors for the event"""
    _log.debug(f"Fetching editors for event {eventId}")

    editors = await event.awaitable_attrs.editors
    editor_list = [Editor(username=editor.username) for editor in editors]

    _log.info(f"Returning {len(editor_list)} editors for event {eventId}")
    return editor_list
