from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cctracker.db import models, with_db
from cctracker.log import get_logger
from cctracker.models.permissions import (
    PermissionRequestBase,
    PermissionRequestResponse,
    PermissionRequestStatus,
)
from cctracker.server.helpers import CurrentUser

log = get_logger(__name__)

api_router = APIRouter(prefix="/admin", tags=["admin"])


@api_router.get("/permission-requests")
async def list_permission_requests(
    _user: Annotated[models.UserData, Security(CurrentUser, scopes=["admin"])],
    db: Annotated[AsyncSession, Depends(with_db)],
) -> list[PermissionRequestResponse]:
    """List all pending permission requests"""
    log.info(f"Admin {_user.username} fetching permission requests")

    stmt = (
        select(models.PermissionRequest)
        .join(models.UserData)
        .order_by(models.PermissionRequest.requested_at)
    )
    results = await db.scalars(stmt)

    requests = []
    for req in results:
        user = await req.awaitable_attrs.user
        requests.append(
            PermissionRequestResponse(
                username=user.username,
                grant_type=req.grant_type,
                status=req.status,
                requested_at=req.requested_at,
                reason=req.reason,
            )
        )

    log.info(f"Returning {len(requests)} permission requests")
    return requests


@api_router.post("/grant-permission/")
async def grant_permission(
    details: PermissionRequestBase,
    admin_user: Annotated[models.UserData, Security(CurrentUser, scopes=["admin"])],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """Grant permission and remove request (manual Keycloak grant required)"""
    log.info(f"Admin {admin_user.username} granting permission to {details.username}")

    stmt = (
        select(models.PermissionRequest)
        .join(models.UserData)
        .where(models.UserData.username == details.username)
    )
    request = await db.scalar(stmt)

    if not request:
        log.warning(f"Permission request not found for {details.username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission request not found"
        )

    request.status = PermissionRequestStatus.GRANTED
    request.granted_by = admin_user.username
    await db.commit()

    log.info(f"Permission granted to {details.username} by {admin_user.username}")
    return PermissionRequestResponse(
        username=user.username,
        grant_type=details.grant_type,
        status=PermissionRequestStatus.GRANTED,
        requested_at=request.requested_at,
        reason=request.reason,
    )


@api_router.delete("/deny-permission/{username}")
async def deny_permission(
    username: str,
    admin_user: Annotated[models.UserData, Security(CurrentUser, scopes=["admin"])],
    db: Annotated[AsyncSession, Depends(with_db)],
):
    """Deny and delete permission request"""
    log.info(f"Admin {admin_user.username} denying permission for {username}")

    stmt = (
        select(models.PermissionRequest)
        .join(models.UserData)
        .where(models.UserData.username == username)
    )
    request = await db.scalar(stmt)

    if not request:
        log.warning(f"Permission request not found for {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission request not found"
        )

    request.status = PermissionRequestStatus.DENIED
    await db.commit()

    log.info(f"Permission denied for {username} by {admin_user.username}")
    return PermissionRequestResponse(
        username=username,
        grant_type=request.grant_type,
        status=PermissionRequestStatus.DENIED,
        requested_at=request.requested_at,
        reason=request.reason,
    )
