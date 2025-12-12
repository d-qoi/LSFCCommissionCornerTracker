from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(256))
    createdBy: Mapped[str] = mapped_column(String(128))
    hostedBy: Mapped[str] = mapped_column(String(64))
    hostedByUrl: Mapped[str] = mapped_column(String(256))

    open_times: Mapped[list["OpenTime"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    seats: Mapped[list["Seat"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    artists: Mapped[list["Artist"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list["SeatAssignment"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    @property
    def seat_count(self) -> int:
        return len(self.seats)

    @property
    def seats_available(self) -> int:
        return sum(s.current_artist is None for s in self.seats)

    @property
    def event_start(self) -> datetime | None:
        """
        Earliest open_time across all OpenTime entries for this event.
        Returns None if there are no open_times.
        """
        if not self.open_times:
            return None
        return min(ot.open_time for ot in self.open_times)

    @property
    def event_end(self) -> datetime | None:
        """
        Latest close_time across all OpenTime entries for this event.
        Returns None if there are no open_times.
        """
        if not self.open_times:
            return None
        return max(ot.close_time for ot in self.open_times)

    @property
    def event_running(self) -> bool:
        if not self.open_times:
            return False

        start = self.event_start
        end = self.event_end

        assert start is not None
        assert end is not None

        return start < datetime.now(timezone.utc) < end

    @property
    def event_open(self) -> bool:
        return any(ot.open_now for ot in self.open_times)



class OpenTime(Base):
    __tablename__ = "open_times"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    event: Mapped["Event"] = relationship(back_populates="open_times")

    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @property
    def open_now(self) -> bool:
        """
        True if the current UTC time is between open_time (inclusive)
        and close_time (exclusive).
        """
        now = datetime.now(timezone.utc)
        return self.open_time <= now < self.close_time


class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(primary_key=True)

    # e.g., seat row/number; you can expand this later (row, section, etc.)
    seat_number: Mapped[int] = mapped_column(Integer())

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    event: Mapped["Event"] = relationship(back_populates="seats")

    assignments: Mapped[list["SeatAssignment"]] = relationship(
        back_populates="seat",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # One seat_number per event (no duplicates).
        UniqueConstraint("event_id", "seat_number", name="uq_seat_event_seat_number"),
    )

    # ---- Convenience properties ----

    @property
    def current_assignment(self) -> "SeatAssignment | None":
        """
        Return the currently active assignment for this seat, if any.

        Active = assignment where ended_at is None.
        If there are multiple active assignments (shouldn't happen if you manage it
        correctly), this returns the first one in the in-memory collection.
        """
        for assignment in self.assignments:
            if assignment.ended_at is None:
                return assignment
        return None

    @property
    def current_artist(self) -> "Artist | None":
        """
        Return the currently assigned artist for this seat, if any.
        """
        assignment = self.current_assignment
        return assignment.artist if assignment is not None else None


class Artist(Base):
    __tablename__ = "transient_artists"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    event: Mapped["Event"] = relationship(back_populates="artists")

    # all the seats this artist has been assigned to over time
    assignments: Mapped[list["SeatAssignment"]] = relationship(
        back_populates="artist",
        cascade="all, delete-orphan",
    )

    imageUrl: Mapped[str] = mapped_column(String())
    profileUrl: Mapped[str] = mapped_column(String(256))
    details: Mapped[str] = mapped_column(String(2048))
    coms_open: Mapped[bool] = mapped_column(Boolean())
    coms_remaining: Mapped[int] = mapped_column(Integer())

    @property
    def current_seat(self) -> "Seat | None":
        """
        Return the current seat this artist is assigned to, if any.
        """
        for assignment in self.assignments:
            if assignment.ended_at is None:
                return assignment.seat
        return None


class SeatAssignment(Base):
    __tablename__ = "seat_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"))
    artist_id: Mapped[int] = mapped_column(ForeignKey("transient_artists.id"))

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    event: Mapped["Event"] = relationship(back_populates="assignments")
    seat: Mapped["Seat"] = relationship(back_populates="assignments")
    artist: Mapped["Artist"] = relationship(back_populates="assignments")

    __table_args__ = (
        # Prevent exact duplicate assignments; you can tweak this as needed.
        UniqueConstraint(
            "event_id",
            "seat_id",
            "artist_id",
            "started_at",
            name="uq_seat_assignment_identity",
        ),
    )
