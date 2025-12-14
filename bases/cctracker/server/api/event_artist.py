from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from valkey.asyncio import Valkey

from cctracker.db import with_db, models
from cctracker.cache import with_vk
from cctracker.log import get_logger
from cctracker.models.artists import RequestNewArtist
from cctracker.models.errors import StandardError, StandardErrorTypes

log = get_logger(__name__)

api_router = APIRouter(prefix="/event")


@api_router.post("/{eventId}/new_artist")
async def create_new_artist(
    eventId: str,
    details: RequestNewArtist,
    response: Response,
    db: Annotated[AsyncSession, Depends(with_db)],
    cache: Annotated[Valkey, Depends(with_vk)],
):

    log.info(f"{eventId}/new_artist called")
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

    wanted_seat: models.Seat | None  = None
    if details.seat:
        log.debug("Trying to add to a seat")
        for seat in event.seats:
            if seat.seat_number == details.seat:
                if seat.current_artist:
                    log.debug("Seat already taken, returning")
                    response.status_code = status.HTTP_409_CONFLICT
                    return StandardError(
                        code=status.HTTP_409_CONFLICT, type=StandardErrorTypes.SEAT_TAKEN
                    )
                else:
                    wanted_seat = seat
                break

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

    seat_assignment = models.SeatAssignment(
        
    )

    new_artist = models.Artist(
        name=details.name,
        slug=details.slug,
    )
