import hashlib
from io import BytesIO
import magic

from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, HTTPException, UploadFile, status
from itsdangerous.exc import BadSignature
from minio import Minio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from valkey.asyncio import Valkey

from cctracker.cache import with_vk
from cctracker.db import with_db, models
from cctracker.fs.core import ALLOWED_IMAGE_TYPES, MAX_FILE_SIZE, with_bucket
from cctracker.log import get_logger
from cctracker.models.artists import (
    Artist,
    ArtistCustomizableDetails,
    ArtistCustomizableDetails_User,
)
from cctracker.server.auth import verify as dc_verify
from cctracker.server.config import config
from cctracker.server.helpers import CurrentUser, OptionalUser
from cctracker.server.seat_expiration_helper import expire_stale_seats

_log = get_logger(__name__)

api_router = APIRouter(prefix="/artist", tags=["artist operations"])


@api_router.get("/{artistId}")
async def get_artist(
    artistId: str,
    db: Annotated[AsyncSession, Depends(with_db)],
    vk: Annotated[Valkey, Depends(with_vk)],
):
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

    await expire_stale_seats(artist.event, db, vk)

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
    event_artist_token: Annotated[str, Cookie()],
    user_data: Annotated[models.UserData | None, Depends(OptionalUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """
    If the current user has the correct cookie, they can update the temporary listing of their seat, or profile for the event.
    If they are logged in, they can also save that data to their account.
    """

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


@api_router.post("/{artistId}/profile_picture")
async def upload_artist_profile_picture(
    artistId: str,
    file: UploadFile,
    event_artist_token: Annotated[str, Cookie()],
    user_data: Annotated[models.UserData | None, Depends(OptionalUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    minio: Annotated[Minio, Depends(with_bucket)],
):
    """
    Update the artist profile picture.
    If they are logged in, update the user profile picture as well.
    """
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

    try:
        ea_token_data = dc_verify(event_artist_token, salt=artist.event.slug)
    except BadSignature as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bad Signature with event_artist_token",
        )

    if ea_token_data.artist_id != artistId:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="artistId mismatch in token",
        )

    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File too large (max 5MB)",
        )

    content = bytearray()
    chunk_size = 1024 * 1024  # 1MB chunk

    while chunk := await file.read(chunk_size):
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File too large (max 5MB)",
            )

    mime_types = magic.from_buffer(bytes(content), mime=True)
    if mime_types not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES.keys())}",
        )

    file_ext = ALLOWED_IMAGE_TYPES[mime_types]

    if user_data:
        object_name = f"profiles/{user_data.username}.{file_ext}"
    else:
        hash = hashlib.sha256(f"{artist.event.slug}:{artistId}".encode()).hexdigest()[
            :16
        ]
        object_name = f"profiles/temp_{hash}.{file_ext}"

    _ = minio.put_object(
        bucket_name=config.minio_bucket,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=mime_types,
    )

    if user_data:
        if user_data.artist_data is None:
            user_artist_data = models.UserArtistData(user_id=user_data.id)
            user_data.artist_data = user_artist_data
            db.add(user_artist_data)

        user_data.artist_data.imageUrl = object_name

    artist.imageUrl = object_name

    await db.commit()


@api_router.get("/saved_details")
async def get_saved_artist_details(
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
):
    """
    If the user is logged in, return the details that have been saved to their account.
    This returns an ArtistCustomizableDetails object.
    """
    if user_data.artist_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No saved artist details"
        )

    return ArtistCustomizableDetails_User.model_validate(
        user_data.artist_data, from_attributes=True, extra="ignore"
    )
