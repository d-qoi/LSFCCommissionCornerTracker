from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from valkey.asyncio import Valkey

from cctracker.cache import with_vk
from cctracker.db import models, with_db
from cctracker.log import get_logger
from cctracker.server.helpers import with_event

log = get_logger(__name__)

_EXPIRATION_CHECK_INTERVAL = 30  # seconds


async def expire_stale_seats(
    event: Annotated[models.Event, Depends(with_event)],
    db: Annotated[AsyncSession, Depends(with_db)],
    vk: Annotated[Valkey, Depends(with_vk)],
) -> None:
    """Check and expire seats using distributed lock"""
    lock_key = f"seat_expiration_lock:{event.id}"

    # Try to acquire lock - only succeeds if key doesn't exist
    # Key auto-expires after _EXPIRATION_CHECK_INTERVAL seconds
    acquired = await vk.set(lock_key, "1", nx=True, ex=_EXPIRATION_CHECK_INTERVAL)

    if not acquired:
        log.debug(
            f"Expiration check already running or recently completed for event {event.slug}"
        )
        return

    await db.refresh(event, ["seats", "artists", "assignments"])

    expired = 0
    utc_now = models.utcnow()

    for seat in event.seats:
        current_seat_assignment = seat.current_assignment
        if current_seat_assignment is None:
            continue

        time_remaining = current_seat_assignment.artist.time_remaining
        if time_remaining is None:
            log.error(
                f"Active artist {current_seat_assignment.artist.slug} has no time_remaining - database inconsistency"
            )
            continue

        if time_remaining <= 0:
            current_seat_assignment.ended_at = utc_now
            expired += 1
            log.debug(
                f"Expired seat for {current_seat_assignment.artist.slug} in event {event.slug}"
            )

    if expired:
        await db.commit()
        log.info(f"Expired {expired} seats in event {event.slug}")
