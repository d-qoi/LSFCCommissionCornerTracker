from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import event, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from cctracker.db import with_db, models
from cctracker.log import get_logger
from cctracker.models.artists import Artist, ArtistCustomizableDetails

_log = get_logger(__name__)

api_router = APIRouter(prefix="/artist")


@api_router.get("/{artistId}")
async def get_artist(artistId: str, db: Annotated[AsyncSession, Depends(with_db)]):
    _log.debug(f"get artist called: {artistId}")

    stmt = (
        select(models.Artist)
        .where(models.Artist.slug == artistId)
        .options(selectinload(models.Artist.assignments),
                 selectinload(models.Artist.event),
            )
    )
    artist = await db.scalar(stmt)

    if artist is None:
        _log.warning(f"{artistId} requested, but not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"{artistId} not found")

    time_remaining = artist.time_remaining

    return Artist(
        name=artist.name,
        slug=artist.slug,
        eventId=artist.event.slug,
        details=artist.details,
        imageUrl=artist.imageUrl,
        profileUrl=artist.profileUrl,
        commissionsOpen=artist.coms_open,
        commissionsRemaining=artist.coms_remaining,
        active=bool(time_remaining),
        timeRemaining=artist.time_remaining
    )

@api_router.post("/{artistId}")
async def update_artist(artistId: str, db: Annotated[AsyncSession, Depends(with_db)]):
    pass
