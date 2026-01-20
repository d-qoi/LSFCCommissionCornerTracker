from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum, auto

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Timezone-aware 'now' for defaults."""
    return datetime.now(timezone.utc)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)

    # General Data
    slug: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(256))
    createdBy: Mapped[str] = mapped_column(String(128))
    hostedBy: Mapped[str] = mapped_column(String(64))
    hostedByUrl: Mapped[str] = mapped_column(String(256))
    seatDuration: Mapped[int] = mapped_column(Integer())  # assumed minutes
    forceClose: Mapped[bool] = mapped_column(Boolean(), default=False)

    open_times: Mapped[list["OpenTime"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    seats: Mapped[list["Seat"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    artists: Mapped[list["Artist"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    assignments: Mapped[list["SeatAssignment"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Owners/editors
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    owner: Mapped["UserData"] = relationship(
        "UserData",
        back_populates="owned_events",
        foreign_keys=[owner_user_id],
    )

    editors: Mapped[list["UserData"]] = relationship(
        "UserData",
        secondary="event_editors",
        back_populates="editable_events",
        passive_deletes=True,
    )

    @property
    def seat_count(self) -> int:
        return len(self.seats)

    @property
    def seats_available(self) -> int:
        return sum(s.current_artist is None for s in self.seats)

    @property
    def event_start(self) -> datetime | None:
        if not self.open_times:
            return None
        return min(ot.open_time for ot in self.open_times)

    @property
    def event_end(self) -> datetime | None:
        if not self.open_times:
            return None
        return max(ot.close_time for ot in self.open_times)

    @property
    def event_running(self) -> bool:
        start = self.event_start
        end = self.event_end
        if start is None or end is None:
            return False
        now = utcnow()
        return start < now < end

    @property
    def event_open(self) -> bool:
        if self.forceClose:
            return False
        return any(ot.open_now for ot in self.open_times)


class OpenTime(Base):
    __tablename__ = "open_times"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    event: Mapped["Event"] = relationship(back_populates="open_times")

    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @property
    def open_now(self) -> bool:
        now = utcnow()
        return self.open_time <= now < self.close_time


class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(primary_key=True)

    seat_number: Mapped[int] = mapped_column(Integer())

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    event: Mapped["Event"] = relationship(back_populates="seats")

    assignments: Mapped[list["SeatAssignment"]] = relationship(
        back_populates="seat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("event_id", "seat_number", name="uq_seat_event_seat_number"),
    )

    @property
    def current_assignment(self) -> "SeatAssignment | None":
        active = [a for a in self.assignments if a.ended_at is None]
        if not active:
            return None
        # prefer the most recent active assignment
        return max(active, key=lambda a: a.started_at)

    @property
    def current_artist(self) -> "Artist | None":
        assignment = self.current_assignment
        return assignment.artist if assignment is not None else None


class Artist(Base):
    __tablename__ = "transient_artists"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    event: Mapped["Event"] = relationship(back_populates="artists")

    assignments: Mapped[list["SeatAssignment"]] = relationship(
        back_populates="artist",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80))
    imageUrl: Mapped[str] = mapped_column(String(), default="unknown_pfp.png")
    profileUrl: Mapped[str] = mapped_column(String(256), default="")
    details: Mapped[str] = mapped_column(String(2048), default="")
    coms_open: Mapped[bool] = mapped_column(Boolean(), default=True)
    coms_remaining: Mapped[int | None] = mapped_column(
        Integer(), nullable=True, default=None
    )

    __table_args__ = (
        UniqueConstraint("event_id", "slug", name="uq_artist_slug_event"),
    )

    @property
    def current_seat(self) -> "Seat | None":
        active = [a for a in self.assignments if a.ended_at is None]
        if not active:
            return None
        latest = max(active, key=lambda a: a.started_at)
        return latest.seat

    @property
    def time_remaining(self) -> int | None:
        """
        Remaining seconds in the current assignment.
        Assumes Event.seatDuration is in minutes.
        """
        active = [a for a in self.assignments if a.ended_at is None]
        if not active:
            return None

        latest = max(active, key=lambda a: a.started_at)
        now = utcnow()

        duration_seconds = int(self.event.seatDuration * 60)
        elapsed_seconds = int((now - latest.started_at).total_seconds())
        return max(0, duration_seconds - elapsed_seconds)

    @property
    def time_since_last_assignment(self) -> int | None:
        """
        Seconds since the most recently ended assignment.
        Returns:
          - None if the artist has never been assigned
          - -1 if currently assigned
          - >=0 seconds since last ended assignment otherwise
        """
        if any(a.ended_at is None for a in self.assignments):
            return -1

        ended = [a for a in self.assignments if a.ended_at is not None]
        if not ended:
            return None

        latest = max(ended, key=lambda a: a.ended_at)  # type: ignore[arg-type]
        assert latest.ended_at is not None

        delta = utcnow() - latest.ended_at
        return int(delta.total_seconds())


class SeatAssignment(Base):
    __tablename__ = "seat_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id", ondelete="CASCADE"))
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("transient_artists.id", ondelete="CASCADE")
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,  # IMPORTANT: callable default
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    event: Mapped["Event"] = relationship(back_populates="assignments")
    seat: Mapped["Seat"] = relationship(back_populates="assignments")
    artist: Mapped["Artist"] = relationship(back_populates="assignments")

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "seat_id",
            "artist_id",
            "started_at",
            name="uq_seat_assignment_identity",
        ),
    )


class EventEditor(Base):
    __tablename__ = "event_editors"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_editor"),)


class UserData(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String())

    owned_events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="owner",
        foreign_keys="Event.owner_user_id",
    )

    editable_events: Mapped[list["Event"]] = relationship(
        "Event",
        secondary="event_editors",
        back_populates="editors",
        passive_deletes=True,
    )

    artist_data: Mapped["UserArtistData | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    permission_requests: Mapped[list["PermissionRequest"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserArtistData(Base):
    __tablename__ = "saved_artists"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,  # enforces 1:1
    )
    user: Mapped["UserData"] = relationship(back_populates="artist_data")

    name: Mapped[str] = mapped_column(String(80))
    imageUrl: Mapped[str] = mapped_column(String(), default="unknown_pfp.png")
    profileUrl: Mapped[str] = mapped_column(String(256), default="")
    details: Mapped[str] = mapped_column(String(2048), default="")


class PermissionRequestStatus(StrEnum):
    PENDING = auto()
    GRANTED = auto()


class PermissionRequest(Base):
    __tablename__ = "permission_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )
    user: Mapped["UserData"] = relationship(back_populates="permission_requests")
    grant_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(), default=PermissionRequestStatus.PENDING
    )
    granted_by: Mapped[str] = mapped_column(String())

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    reason: Mapped[str] = mapped_column(String(512), default="")

    __table_args__ = (
        UniqueConstraint("user_id", "grant_type", name="uq_user_grant_type"),
    )
