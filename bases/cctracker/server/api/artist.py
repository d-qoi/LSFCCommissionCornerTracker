from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from itsdangerous.exc import BadSignature
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from cctracker.db import with_db, models
from cctracker.log import get_logger
from cctracker.models.artists import Artist, ArtistCustomizableDetails, ArtistSummary
from cctracker.server.auth import verify as dc_verify
from cctracker.server.helpers import CurrentUser, OptionalUser

_log = get_logger(__name__)

api_router = APIRouter(prefix="/artist")


@api_router.get("/{artistId}")
async def get_artist(artistId: str, db: Annotated[AsyncSession, Depends(with_db)]):
    """
    Gets the general information about the provided {artistId}, and returns an Artist model.
    """
    _log.debug(f"get artist called: {artistId}")

    stmt = (
        select(models.Artist)
        .where(models.Artist.slug == artistId)
        .options(
            selectinload(models.Artist.assignments),
            selectinload(models.Artist.event),
        )
    )
    artist = await db.scalar(stmt)

    if artist is None:
        _log.warning(f"{artistId} requested, but not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{artistId} not found"
        )

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
        timeRemaining=artist.time_remaining,
    )


@api_router.post("/{artistId}")
async def update_artist(
    artistId: str,
    artistDetails: ArtistCustomizableDetails,
    saveDetails: bool,
    event_artist_token: Annotated[str | None, Cookie()],
    user_data: Annotated[models.UserData | None, Depends(OptionalUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """
    If the current user has the correct cookie, they can update the temporary listing of their seat, or profile for the event.
    If they are logged in, they can also save that data to their account.
    """
    if event_artist_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="no event_artist_token"
        )

    try:
        ea_token_data = dc_verify(event_artist_token, salt=artistDetails.eventId)
    except BadSignature as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad Signature with event_artist_token",
        )

    if ea_token_data.artist_id != artistId:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="artist slug mismatch in token",
        )

    elif ea_token_data.event_id != artistDetails.eventId:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="event id mismatch in token and submitted details",
        )

    stmt = (
        select(models.Artist)
        .where(models.Artist.slug == artistId)
        .options(
            selectinload(models.Artist.assignments),
            selectinload(models.Artist.event),
        )
    )
    artist = await db.scalar(stmt)

    if artist is None:
        _log.warning(f"{artistId} requested, but not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{artistId} not found"
        )

    artist.name = artistDetails.name
    artist.details = artistDetails.details
    artist.profileUrl = str(artistDetails.profileUrl)
    artist.coms_open = artistDetails.commissionsOpen
    artist.coms_remaining = artistDetails.commissionsRemaining

    await db.commit()

    if saveDetails and user_data:
        if user_data.artist_data is None:
            user_data.artist_data = models.UserArtistData()

        user_data.artist_data.name = artist.name
        user_data.artist_data.profileUrl = artist.profileUrl
        user_data.artist_data.details = artist.details

        await db.commit()


@api_router.get("/saved_details")
async def get_saved_artist_details(
    user: Annotated[models.UserData | None, Depends(CurrentUser)],
):
    """
    If the user is logged in, return the details that have been saved to their account.
    This returns an ArtistCustomizableDetails object.
    """
    pass
