from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_name: Mapped[str] = mapped_column(String(256))
    open_times: Mapped[list["OpenTime"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    num_seats: Mapped[int]
    seats: Mapped[list["Seat"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    artists: Mapped[list["Artist"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class OpenTime(Base):
    __tablename__ = "open_times"

    id: Mapped[int] = mapped_column(primary_key=True)
    event: Mapped["Event"] = relationship(back_populates="open_times")
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[str] = mapped_column(DateTime(timezone=True))

class Seat(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    event: Mapped["Event"] = relationship(back_populates="seats")
    artist: Mapped["Artist"] = relationship(back_populates="seat")

class Artist(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    event: Mapped["Event"] = relationship(back_populates="artists")

