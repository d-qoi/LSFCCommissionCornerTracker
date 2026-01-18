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
from cctracker.models.artists import RequestNewArtist
from cctracker.models.errors import StandardError, StandardErrorTypes
from cctracker.server.auth import EventArtistToken, sign as dc_sign, verify as dc_verify
from cctracker.server.helpers import CurrentUser

log = get_logger(__name__)

api_router = APIRouter(prefix="/event")


class EventArtistTokenResponse(BaseModel):
    token: str


@api_router.post("/{eventId}/artist/new")
async def create_new_artist(
    eventId: str,
    details: RequestNewArtist,
    response: Response,
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Create a new artist token, create the db entry for artist, and return the token.
    The artist will be assigned a seat, as soon as the token is validated at /{eventId}/artist/claim
    """

    log.info(f"{eventId}/artist/new_artist called by {user_data.username}")
    log.debug(f"{details.model_dump()}")
    event_stmt = (
        select(models.Event)
        .where(models.Event.slug == eventId)
        .options(
            selectinload(models.Event.seats), selectinload(models.Event.assignments)
        )
    )
    event = await db.scalar(event_stmt)

    if event is None:
        log.debug("Event doesn't exist")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{eventId} not found"
        )

    if event.slug not in [
        editable_event.slug for editable_event in user_data.editable_events
    ]:
        log.debug(f"{user_data.username} can not edit {eventId}")
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
        f"{eventId}:{details.slug}",
        mapping={
            "status": ArtistSeatStatus.pending_creation,
            "seat": wanted_seat.seat_number,
            "token_uuid": event_artist_token.uuid,
        },
    )

    log.debug(f"Returning token, pending artist acceptance.")

    return EventArtistTokenResponse(token=dc_sign(event_artist_token, salt=eventId))


@api_router.get("/{eventId}/artist/token/{artistId}")
async def recreate_artist_token(
    eventId: str,
    artistId: str,
    response: Response,
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Recreate a token for an existing artist.
    """
    log.info(f"{eventId}/tokens/{artistId} called by {user_data.username}")

    event_stmt = select(models.Event).where(models.Event.slug == eventId)
    event = await db.scalar(event_stmt)

    if event is None:
        log.debug("Event doesn't exist")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{eventId} not found"
        )

    if event.slug not in [
        editable_event.slug for editable_event in user_data.editable_events
    ]:
        log.debug(f"{user_data.username} can not edit {eventId}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to edit this event.",
        )

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
        event_id=eventId, artist_id=artistId, uuid=uuid4()
    )

    log.debug(f"Recreated artist token: {event_artist_token}")

    _ = await cache.hset(
        f"{eventId}:{artistId}",
        mapping={"token_uuid": event_artist_token.uuid},
    )

    log.info(f"Token recreated for artist {artistId} in {eventId}")

    return EventArtistTokenResponse(token=dc_sign(event_artist_token, salt=eventId))


@api_router.get("/{eventId}/artist/claim")
async def claim_artist_seat(
    eventId: str,
    token: str,
    response: Response,
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):
    """
    Artist claims their seat using the token provided by event organizer.
    Sets the token as a cookie for future requests.
    """
    log.info(f"{eventId}/artist/claim called with token")

    try:
        token_data = dc_verify(token, salt=eventId)
    except Exception as e:
        log.warning(f"Invalid token signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    artist_id = token_data.artist_id
    cache_key = f"{eventId}:{artist_id}"

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

    event_stmt = (
        select(models.Event)
        .where(models.Event.slug == eventId)
        .options(selectinload(models.Event.seats))
    )
    event = await db.scalar(event_stmt)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {eventId} not found"
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
        log.info(f"Artist {artist_id} claimed seat {seat_number} in {eventId}")

    await cache.hset(cache_key, "status", ArtistSeatStatus.active)

    response.set_cookie(
        key="event_artist_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,  # 7 days
    )

    log.info(f"Token set as cookie for artist {artist_id}")

