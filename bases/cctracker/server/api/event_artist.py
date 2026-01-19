from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from valkey.asyncio import Valkey

from cctracker.cache.core import ArtistSeatStatus
from cctracker.db import with_db, models
from cctracker.cache import with_vk
from cctracker.log import get_logger
from cctracker.models.artists import ArtistCustomizableDetails, RequestNewArtist
from cctracker.models.errors import StandardError, StandardErrorTypes
from cctracker.server.auth import EventArtistToken, sign as dc_sign, verify as dc_verify
from cctracker.server.helpers import CurrentUser, require_event_editor, with_event

log = get_logger(__name__)

api_router = APIRouter(prefix="/event")


class EventArtistTokenResponse(BaseModel):
    token: str


@api_router.post("/{eventId}/artist/new")
async def create_new_artist(
    details: RequestNewArtist,
    response: Response,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Create a new artist token, create the db entry for artist, and return the token.
    The artist will be assigned a seat, as soon as the token is validated at /{eventId}/artist/claim
    """

    log.info(f"{event.slug}/artist/new_artist called by {user_data.username}")
    log.debug(f"{details.model_dump()}")

    if event.slug not in [
        editable_event.slug for editable_event in user_data.editable_events
    ]:
        log.debug(f"{user_data.username} can not edit {event.slug}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to edit this event.",
        )

    wanted_seat: models.Seat | None = None
    if details.seat:
        log.debug("Trying to add to a seat")
        for seat in event.seats:
            if seat.seat_number == details.seat:
                if seat.current_artist:
                    log.debug("Seat already taken, returning")
                    response.status_code = status.HTTP_409_CONFLICT
                    return StandardError(
                        code=status.HTTP_409_CONFLICT,
                        type=StandardErrorTypes.SEAT_TAKEN,
                    )
                else:
                    wanted_seat = seat
                break

    if wanted_seat is None:
        log.debug("Seat requested does not exist")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return StandardError(
            code=status.HTTP_400_BAD_REQUEST, type=StandardErrorTypes.INVALID_SEAT
        )

    artist_stmt = select(models.Artist).where(
        (models.Artist.slug == details.slug)
        & (models.Artist.event_id == details.eventId)
    )
    artist_exists = await db.scalar(artist_stmt)

    if artist_exists:
        log.debug("Artist slug already exists")
        response.status_code = status.HTTP_409_CONFLICT
        return StandardError(
            code=status.HTTP_409_CONFLICT, type=StandardErrorTypes.SLUG_EXISTS
        )

    new_artist = models.Artist(
        name=details.name,
        slug=details.slug,
    )

    event.artists.append(new_artist)
    db.add(new_artist)

    await db.commit()

    log.info(f"Artist ({details.name}) assigned to {details.slug} for {eventId}")

    event_artist_token = EventArtistToken(
        event_id=eventId, artist_id=details.slug, uuid=uuid4()
    )

    log.debug(f"new artist token: {event_artist_token}")

    _ = await cache.hset(
        f"{event.slug}:{details.slug}",
        mapping={
            "status": ArtistSeatStatus.pending_creation,
            "seat": wanted_seat.seat_number,
            "token_uuid": event_artist_token.uuid,
            "locked": "0",
        },
    )

    log.debug(f"Returning token, pending artist acceptance.")

    return EventArtistTokenResponse(token=dc_sign(event_artist_token, salt=event.slug))


@api_router.get("/{eventId}/artist/token/{artistId}")
async def recreate_artist_token(
    artistId: str,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Recreate a token for an existing artist.
    """
    log.info(f"{event.slug}/tokens/{artistId} called by {user_data.username}")

    artist_stmt = select(models.Artist).where(
        (models.Artist.slug == artistId) & (models.Artist.event_id == event.id)
    )
    artist = await db.scalar(artist_stmt)

    if not artist:
        log.debug(f"Artist {artistId} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Artist {artistId} not found"
        )

    event_artist_token = EventArtistToken(
        event_id=event.slug, artist_id=artistId, uuid=uuid4()
    )

    log.debug(f"Recreated artist token: {event_artist_token}")

    _ = await cache.hset(
        f"{event.slug}:{artistId}",
        mapping={"token_uuid": event_artist_token.uuid},
    )

    log.info(f"Token recreated for artist {artistId} in {event.slug}")

    return EventArtistTokenResponse(token=dc_sign(event_artist_token, salt=event.slug))


@api_router.get("/{eventId}/artist/claim")
async def claim_artist_seat(
    token: str,
    response: Response,
    event: Annotated[models.Event, Depends(with_event)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Artist claims their seat using the token provided by event organizer.
    Sets the token as a cookie for future requests.
    """
    log.info(f"{event.slug}/artist/claim called with token")

    try:
        token_data = dc_verify(token, salt=event.slug)
    except Exception as e:
        log.warning(f"Invalid token signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    artist_id = token_data.artist_id
    cache_key = f"{event.slug}:{artist_id}"

    cached_data = await cache.hgetall(cache_key)

    if not cached_data:
        log.warning(f"No cached data for {cache_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist assignment not found"
        )

    if cached_data.get("token_uuid") != str(token_data.uuid):
        log.warning(f"Token UUID mismatch for {artist_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated",
        )

    artist_stmt = select(models.Artist).where(
        (models.Artist.slug == artist_id) & (models.Artist.event_id == event.id)
    )
    artist = await db.scalar(artist_stmt)

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artist {artist_id} not found",
        )

    seat_number = int(cached_data.get("seat", 0))
    seat = next((s for s in event.seats if s.seat_number == seat_number), None)

    if not seat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned seat no longer exists",
        )

    if seat.current_artist and seat.current_artist.id != artist.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Seat is already occupied"
        )

    if not seat.current_artist:
        assignment = models.SeatAssignment(
            event_id=event.id,
            seat_id=seat.id,
            artist_id=artist.id,
        )
        db.add(assignment)
        await db.commit()
        log.info(f"Artist {artist_id} claimed seat {seat_number} in {event.slug}")

    await cache.hset(cache_key, "status", ArtistSeatStatus.active)

    response.set_cookie(
        key="event_artist_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    log.info(f"Token set as cookie for artist {artist_id}")
    return True


class ArtistEventLock(BaseModel):
    locked: bool


@api_router.post("/event/{eventId}/artist/{artistId}/lock")
async def set_artist_locked_for_event(
    artistId: str,
    lockStatus: ArtistEventLock,
    event: Annotated[models.Event, Depends(require_event_editor)],
    _user_data: Annotated[models.UserData, Depends(CurrentUser)],
    cache: Annotated[Valkey, Depends(with_vk)],
):

    cache_key = f"{event.slug}:{artistId}"

    cached_data = await cache.hget(cache_key, "locked")

    if cached_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist not in cache"
        )

    _ = await cache.hset(cache_key, "locked", int(lockStatus.locked))

    return lockStatus


@api_router.post("/event/{eventId}/artist/{artistId}/lock")
async def get_artist_locked_status_for_event(
    _eventId: str,
    artistId: str,
    event: Annotated[models.Event, Depends(require_event_editor)],
    _user_data: Annotated[models.UserData, Depends(CurrentUser)],
    cache: Annotated[Valkey, Depends(with_vk)],
):

    cache_key = f"{event.slug}:{artistId}"

    cached_data = await cache.hget(cache_key, "locked")

    if cached_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artist not in cache"
        )

    return ArtistEventLock(locked=bool(int(cached_data)))


@api_router.patch("/{eventId}/artist/{artistId}")
async def update_artist_details(
    eventId: str,
    artistId: str,
    details: ArtistCustomizableDetails,
    response: Response,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """
    Event editors can update artist profile details.
    """
    log.info(f"{event.slug}/artist/{artistId} update called by {user_data.username}")

    artist_stmt = select(models.Artist).where(
        (models.Artist.slug == artistId) & (models.Artist.event_id == event.id)
    )
    artist = await db.scalar(artist_stmt)

    if not artist:
        log.debug(f"Artist {artistId} not found")
        response.status_code = status.HTTP_404_NOT_FOUND
        return StandardError(
            code=status.HTTP_404_NOT_FOUND,
            type=StandardErrorTypes.ARTIST_NOT_FOUND,
        )

    artist.name = details.name
    artist.details = details.details
    artist.profileUrl = str(details.profileUrl)
    artist.coms_open = details.commissionsOpen
    artist.coms_remaining = details.commissionsRemaining

    await db.commit()

    log.info(f"Artist {artistId} updated by {user_data.username}")


class AssignSeat(BaseModel):
    seat: int


@api_router.put("/{eventId}/artist/{artistId}/seat")
async def assign_artist_to_seat(
    artistId: str,
    seat_request: AssignSeat,
    response: Response,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Assign an existing artist to a seat.
    Ends any current assignment and creates a new one.
    """
    log.info(f"{event.slug}/artist/{artistId}/seat PUT called by {user_data.username}")

    artist_stmt = (
        select(models.Artist)
        .where((models.Artist.slug == artistId) & (models.Artist.event_id == event.id))
        .options(selectinload(models.Artist.assignments))
    )
    artist = await db.scalar(artist_stmt)

    if not artist:
        log.debug(f"Artist {artistId} not found")
        response.status_code = status.HTTP_404_NOT_FOUND
        return StandardError(
            code=status.HTTP_404_NOT_FOUND,
            type=StandardErrorTypes.ARTIST_NOT_FOUND,
        )

    seat = next((s for s in event.seats if s.seat_number == seat_request.seat), None)

    if not seat:
        log.debug(f"Seat {seat_request.seat} not found")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return StandardError(
            code=status.HTTP_400_BAD_REQUEST,
            type=StandardErrorTypes.INVALID_SEAT,
        )

    if seat.current_artist and seat.current_artist.id != artist.id:
        log.debug(f"Seat {seat_request.seat} already occupied")
        response.status_code = status.HTTP_409_CONFLICT
        return StandardError(
            code=status.HTTP_409_CONFLICT,
            type=StandardErrorTypes.SEAT_TAKEN,
        )

    # End current assignment if exists
    active_assignment = next(
        (a for a in artist.assignments if a.ended_at is None), None
    )
    if active_assignment:
        active_assignment.ended_at = models.utcnow()

    # Create new assignment
    new_assignment = models.SeatAssignment(
        event_id=event.id,
        seat_id=seat.id,
        artist_id=artist.id,
    )
    db.add(new_assignment)
    await db.commit()

    await cache.hset(
        f"{event.slug}:{artistId}",
        mapping={"status": ArtistSeatStatus.active, "seat": seat_request.seat},
    )

    log.info(
        f"Artist {artistId} assigned to seat {seat_request.seat} by {user_data.username}"
    )


@api_router.delete("/{eventId}/artist/{artistId}/seat")
async def remove_artist_from_seat(
    artistId: str,
    response: Response,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Remove artist from their current seat but keep them in the event.
    Ends the current seat assignment.
    """
    log.info(
        f"{event.slug}/artist/{artistId}/seat delete called by {user_data.username}"
    )

    artist_stmt = (
        select(models.Artist)
        .where((models.Artist.slug == artistId) & (models.Artist.event_id == event.id))
        .options(selectinload(models.Artist.assignments))
    )
    artist = await db.scalar(artist_stmt)

    if not artist:
        log.debug(f"Artist {artistId} not found")
        response.status_code = status.HTTP_404_NOT_FOUND
        return StandardError(
            code=status.HTTP_404_NOT_FOUND,
            type=StandardErrorTypes.ARTIST_NOT_FOUND,
        )

    active_assignment = next(
        (a for a in artist.assignments if a.ended_at is None), None
    )

    if not active_assignment:
        log.debug(f"Artist {artistId} has no active seat")
        response.status_code = status.HTTP_404_NOT_FOUND
        return StandardError(
            code=status.HTTP_404_NOT_FOUND,
            type=StandardErrorTypes.NO_ACTIVE_SEAT,
        )

    active_assignment.ended_at = models.utcnow()
    await db.commit()

    await cache.hset(f"{event.slug}:{artistId}", "status", ArtistSeatStatus.inactive)

    log.info(f"Artist {artistId} removed from seat by {user_data.username}")


@api_router.delete("/{eventId}/artist/{artistId}")
async def remove_artist_from_event(
    artistId: str,
    response: Response,
    event: Annotated[models.Event, Depends(require_event_editor)],
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Remove artist completely from the event.
    Deletes the artist record and all associated seat assignments.
    """
    log.info(f"{event.slug}/artist/{artistId} delete called by {user_data.username}")

    artist_stmt = select(models.Artist).where(
        (models.Artist.slug == artistId) & (models.Artist.event_id == event.id)
    )
    artist = await db.scalar(artist_stmt)

    if not artist:
        log.debug(f"Artist {artistId} not found")
        response.status_code = status.HTTP_404_NOT_FOUND
        return StandardError(
            code=status.HTTP_404_NOT_FOUND,
            type=StandardErrorTypes.ARTIST_NOT_FOUND,
        )

    await db.delete(artist)
    await db.commit()

    await cache.delete(f"{event.slug}:{artistId}")

    log.info(f"Artist {artistId} removed from event by {user_data.username}")
