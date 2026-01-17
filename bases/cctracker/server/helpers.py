from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cctracker.db import with_db, models
from cctracker.log import get_logger
from cctracker.server.auth import CurrentPrincipal, Principal

log = get_logger(__name__)

async def with_event(eventId: str, db: Annotated[AsyncSession, Depends(with_db)]) -> models.Event:
    stmt = select(models.Event).where(models.Event.slug == eventId).options(
        selectinload(models.Event.open_times),
        selectinload(models.Event.seats).selectinload(models.Seat.assignments),
        selectinload(models.Event.artists),
        selectinload(models.Event.assignments)
    )
    event = await db.scalar(stmt)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"{eventId} not found")
    return event



@dataclass(frozen=True, slots=True)
class CurrentUser:
    optional: bool = False

    async def __call__(
        self,
        principal: Annotated[Principal | None, Depends(CurrentPrincipal(optional=True))],
        db: Annotated[AsyncSession, Depends(with_db)],
    ):
        if principal is None:
            if self.optional:
                return None
            raise HTTPException(status_code=401, detail="Not authenticated")

        # example: lookup by Keycloak subject in `UserData.sub`
        result = await db.execute(select(models.UserData).where(models.UserData.username == principal.sub))
        user = result.scalar_one_or_none()

        if user is None:
            # depends on your app policy:
            # - create-on-first-login
            # - or 403/404
            if self.optional:
                return None
            raise HTTPException(status_code=403, detail="User not provisioned")

        return user


OptionalUser = CurrentUser(optional=True)
