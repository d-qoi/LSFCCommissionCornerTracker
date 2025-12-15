from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cctracker.db import with_db, models
from cctracker.log import get_logger

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
