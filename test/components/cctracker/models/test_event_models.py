# test_events.py
import pytest
from datetime import datetime, timedelta, timezone
from cctracker.models.events import (
    OpenTimes,
    NewEvent,
)  # <-- change to your actual module


# ---------- Tests for OpenTimes ----------


def test_open_times_valid_range():
    now = datetime.now(timezone.utc)
    ot = OpenTimes(
        open_time=now,
        close_time=now + timedelta(hours=2),
    )
    assert ot.open_time < ot.close_time
    assert ot.close_time - ot.open_time == timedelta(hours=2)


def test_open_times_open_after_close_raises():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="Open Time after Close Time."):
        _ = OpenTimes(
            open_time=now + timedelta(hours=1),
            close_time=now,
        )


def test_open_times_under_one_hour_raises():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="Close is under an hour from open."):
        _ = OpenTimes(
            open_time=now,
            close_time=now + timedelta(minutes=59),
        )


def test_open_times_over_twenty_four_hours_raises():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="Close is over 24hours from open."):
        _ = OpenTimes(
            open_time=now,
            close_time=now + timedelta(hours=24, minutes=1),
        )


# ---------- Tests for NewEvent.openTimes validator ----------


def make_event(open_times: list[OpenTimes]) -> NewEvent:
    """Helper to construct a minimal valid NewEvent."""
    return NewEvent(
        name="Test Event",
        slug="test-event",
        hostedBy="Tester",
        duration=100,
        hostedByUrl="https://example.com",  # pydantic will coerce to HttpUrl
        seats=10,
        openTimes=open_times,
    )


def test_new_event_sorts_open_times_and_allows_non_overlapping():
    base = datetime.now(timezone.utc) + timedelta(days=1)

    # Unsorted, but non-overlapping
    t1 = OpenTimes(
        open_time=base + timedelta(hours=3),
        close_time=base + timedelta(hours=5),
    )
    t0 = OpenTimes(
        open_time=base + timedelta(hours=0),
        close_time=base + timedelta(hours=2),
    )

    event = make_event([t1, t0])

    # openTimes should be sorted by open_time
    assert len(event.openTimes) == 2
    assert event.openTimes[0].open_time < event.openTimes[1].open_time
    assert event.openTimes[0].open_time == t0.open_time
    assert event.openTimes[1].open_time == t1.open_time


def test_new_event_allows_almost_week():
    base = datetime.now(timezone.utc) + timedelta(days=1)

    # t0: [base, base+2h], t1: [base+2h, base+4h] (touching at boundary)
    t0 = OpenTimes(
        open_time=base,
        close_time=base + timedelta(hours=2),
    )
    t1 = OpenTimes(
        open_time=base + timedelta(days=7, hours=2),
        close_time=base + timedelta(days=7, hours=4),
    )

    # Should not raise, time delta is just one a week
    event = make_event([t0, t1])
    assert len(event.openTimes) == 2


def test_new_event_raises_if_more_than_week():
    base = datetime.now(timezone.utc) + timedelta(days=1)

    # t0: [base, base+2h], t1: [base+2h, base+4h] (touching at boundary)
    t0 = OpenTimes(
        open_time=base,
        close_time=base + timedelta(hours=2),
    )
    t1 = OpenTimes(
        open_time=base + timedelta(days=7, hours=4),
        close_time=base + timedelta(days=7, hours=5),
    )

    # Should not raise, time delta is just one a week
    with pytest.raises(ValueError, match="Open time can't be a week after last close time."):
        _ = make_event([t0, t1])


def test_new_event_allows_touching_but_not_overlapping_intervals():
    base = datetime.now(timezone.utc) + timedelta(days=1)

    # t0: [base, base+2h], t1: [base+2h, base+4h] (touching at boundary)
    t0 = OpenTimes(
        open_time=base,
        close_time=base + timedelta(hours=2),
    )
    t1 = OpenTimes(
        open_time=base + timedelta(hours=2),
        close_time=base + timedelta(hours=4),
    )

    # Should NOT raise, because prev.close_time == curr.open_time is allowed
    event = make_event([t0, t1])
    assert len(event.openTimes) == 2


def test_new_event_overlapping_intervals_raise():
    base = datetime.now(timezone.utc) + timedelta(days=1)

    # Overlapping by 1 hour
    t0 = OpenTimes(
        open_time=base,
        close_time=base + timedelta(hours=3),
    )
    t1 = OpenTimes(
        open_time=base + timedelta(hours=2),
        close_time=base + timedelta(hours=4),
    )

    with pytest.raises(ValueError, match="must not overlap"):
        _ = make_event([t0, t1])


def test_new_event_allows_zero_or_one_interval_covering_now():
    now = datetime.now(timezone.utc)

    # Interval that covers "now"
    t_now = OpenTimes(
        open_time=now - timedelta(hours=1),
        close_time=now + timedelta(hours=1),
    )

    # Interval entirely in the past, does NOT cover now
    t_past = OpenTimes(
        open_time=now - timedelta(hours=3),
        close_time=now - timedelta(hours=2),
    )

    # Should be fine: only one interval contains "today" moment
    event = make_event([t_past, t_now])
    assert len(event.openTimes) == 2
    # Make sure both stayed in the list
    assert any(ot.open_time == t_now.open_time for ot in event.openTimes)
    assert any(ot.open_time == t_past.open_time for ot in event.openTimes)


def test_new_event_allows_empty_open_times():
    event = make_event([])
    assert event.openTimes == []
