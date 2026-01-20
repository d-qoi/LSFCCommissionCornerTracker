from io import BytesIO
import magic

from enum import StrEnum, auto
from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from minio import Minio
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from cctracker.db import models, with_db
from cctracker.fs import MAX_FILE_SIZE, with_bucket
from cctracker.fs.core import ALLOWED_IMAGE_TYPES
from cctracker.models.artists import (
    ArtistCustomizableDetails,
    ArtistCustomizableDetails_User,
)
from cctracker.models.permissions import (
    PermissionRequestInfo,
    PermissionRequestStatus,
    PermissionRequestType,
)
from cctracker.server.helpers import CurrentUser
from cctracker.server.config import config
from cctracker.log import get_logger

log = get_logger(__name__)

api_router = APIRouter(prefix="/user")


@api_router.post("/request_permissions")
async def request_permissions(
    response: Response,
    request_info: PermissionRequestInfo,
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    log.info(
        f"User {user_data.username} requesting permission: {request_info.grant_type} with status {request_info.status}"
    )

    permission_requests = await user_data.awaitable_attrs.permission_requests

    existing = next(
        (r for r in permission_requests if r.grant_type == request_info.grant_type),
        None,
    )

    if request_info.status == PermissionRequestStatus.NEW:
        if existing:
            log.warning(
                f"User {user_data.username} already has pending request for {request_info.grant_type}"
            )
            response.status_code = status.HTTP_409_CONFLICT
            return PermissionRequestInfo(
                username=user_data.username,
                status=existing.status,
                grant_type=existing.grant_type,
                reason=existing.reason,
            )

        new_request = models.PermissionRequest(
            user_id=user_data.id,
            grant_type=request_info.grant_type,
            reason=request_info.reason,
        )
        db.add(new_request)
        await db.commit()
        log.info(
            f"Created permission request for {user_data.username}: {request_info.grant_type}"
        )
        request_info.status = PermissionRequestStatus.PENDING
        request_info.username = user_data.username
        return request_info

    elif request_info.status == PermissionRequestStatus.CANCEL:
        if not existing:
            log.warning(
                f"User {user_data.username} tried to cancel non-existent request: {request_info.grant_type}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No permission request found for {request_info.grant_type}",
            )

        await db.delete(existing)
        await db.commit()
        log.info(
            f"User {user_data.username} cancelled permission request: {request_info.grant_type}"
        )
        return PermissionRequestInfo(
            username=user_data.username,
            status=PermissionRequestStatus.CANCEL,
            grant_type=request_info.grant_type,
            reason="User Canceled Request",
        )


@api_router.get("/requested_permissions")
async def get_requested_permissions(
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
):
    log.debug(f"Fetching permission requests for {user_data.username}")

    permission_requests: list[models.PermissionRequest] = (
        await user_data.awaitable_attrs.permission_requests
    )

    resp: list[PermissionRequestInfo] = []
    for permission_request in permission_requests:
        resp.append(
            PermissionRequestInfo(
                username=user_data.username,
                status=permission_request.status,
                grant_type=permission_request.grant_type,
                reason=permission_request.reason,
            )
        )

    log.info(f"Returning {len(resp)} permission requests for {user_data.username}")
    return resp


@api_router.post("/artist_details")
async def update_artist_details(
    details: ArtistCustomizableDetails_User,
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """Update user's saved artist profile details"""
    log.info(f"User {user_data.username} updating artist details")

    artist_data = await user_data.awaitable_attrs.artist_data

    if not artist_data:
        log.debug(f"Creating new artist data for {user_data.username}")
        artist_data = models.UserArtistData(user_id=user_data.id)
        db.add(artist_data)

    artist_data.name = details.name
    artist_data.details = details.details
    artist_data.profileUrl = str(details.profileUrl)

    await db.commit()
    log.info(f"Updated artist details for {user_data.username}")
    return details


@api_router.get("/artist_details")
async def get_artist_details(
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
):
    """Get user's saved artist profile details"""
    log.debug(f"Fetching artist details for {user_data.username}")

    if not user_data.artist_data:
        log.warning(f"User {user_data.username} has no saved artist details")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No saved artist details"
        )

    log.info(f"Returning artist details for {user_data.username}")
    return ArtistCustomizableDetails_User(
        name=user_data.artist_data.name,
        details=user_data.artist_data.details,
        profileUrl=user_data.artist_data.profileUrl,
        imageUrl=user_data.artist_data.imageUrl,
    )


@api_router.post("/profile_picture")
async def upload_profile_picture(
    file: UploadFile,
    user_data: Annotated[models.UserData, Depends(CurrentUser)],
    db: Annotated[AsyncSession, Depends(with_db)],
    minio: Annotated[Minio, Depends(with_bucket)],
):
    log.info(f"User {user_data.username} uploading profile picture: {file.filename}")

    if file.size and file.size > MAX_FILE_SIZE:
        log.warning(
            f"User {user_data.username} attempted to upload file too large: {file.size} bytes"
        )
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File too large (max 5MB)",
        )

    content = bytearray()
    chunk_size = 1024 * 1024  # 1MB chunk

    while chunk := await file.read(chunk_size):
        content.extend(chunk)
        if len(content) > MAX_FILE_SIZE:
            log.warning(
                f"User {user_data.username} file exceeded size limit during read: {len(content)} bytes"
            )
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File too large (max 5MB)",
            )

    log.debug(f"Read {len(content)} bytes from {file.filename}")

    mime_types = magic.from_buffer(bytes(content), mime=True)
    if mime_types not in ALLOWED_IMAGE_TYPES:
        log.warning(
            f"User {user_data.username} uploaded invalid image type: {mime_types}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES.keys())}",
        )

    log.debug(f"Validated image type: {mime_types}")

    artist_data = user_data.artist_data
    if not artist_data:
        log.debug(f"Creating artist data for {user_data.username}")
        artist_data = models.UserArtistData(user_id=user_data.id)
        db.add(artist_data)

    file_ext = ALLOWED_IMAGE_TYPES[mime_types]
    object_name = f"profiles/{user_data.username}.{file_ext}"

    log.debug(f"Uploading to MinIO: {object_name}")

    _ = minio.put_object(
        config.minio_bucket,
        object_name,
        BytesIO(content),
        len(content),
        content_type=mime_types,
    )

    artist_data.imageUrl = object_name
    await db.commit()

    log.info(
        f"Successfully uploaded profile picture for {user_data.username}: {object_name}"
    )
    return {"imageUrl": object_name}
