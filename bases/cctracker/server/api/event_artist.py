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
from cctracker.server.auth import EventArtistToken, sign as dc_sign
from cctracker.server.helpers import CurrentUser

log = get_logger(__name__)

api_router = APIRouter(prefix="/event")


class EventArtistTokenResponse(BaseModel):
    token: str


@api_router.post("/{eventId}/new_artist")
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
    The artist will be assigned a seat, as soon as the token is validated at /{eventId}/claim
    """

    log.info(f"{eventId}/new_artist called by {user_data.username}")
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

    _ = cache.hset(
        f"{eventId}:{details.slug}",
        mapping={
            "status": ArtistSeatStatus.pending_creation,
            "seat": wanted_seat.seat_number,
            "token_uuid": event_artist_token.uuid,
        },
    )

    log.debug(f"Returning token, pending artist acceptance.")

    return EventArtistTokenResponse(token=dc_sign(event_artist_token, salt=eventId))


@api_router.get("/{eventId}/tokens/{artistId}")
async def recreate_artist_token(
    eventId: str,
    artistId: str,
    response: Response,
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):

    pass
