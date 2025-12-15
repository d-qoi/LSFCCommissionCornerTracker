from httpx import AsyncClient
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta

from cctracker.db.models import Base, Event, OpenTime, Seat, Artist
from cctracker.models.events import NewEvent, OpenTimes


@pytest.fixture
def sample_future_open_times():
    """Sample open/close times for events"""
    now = datetime.now(timezone.utc)
    return [
        OpenTimes(
            open_time=now + timedelta(days=3, hours=1),
            close_time=now + timedelta(days=3, hours=8),
        ),
        OpenTimes(
            open_time=now + timedelta(days=4, hours=1),
            close_time=now + timedelta(days=4, hours=8),
        ),
    ]


@pytest.fixture
def sample_current_open_times():
    """Sample open/close times for events"""
    now = datetime.now(timezone.utc)
    return [
        OpenTimes(
            open_time=now + timedelta(days=0, hours=-1),
            close_time=now + timedelta(days=0, hours=8),
        ),
        OpenTimes(
            open_time=now + timedelta(days=1, hours=1),
            close_time=now + timedelta(days=1, hours=8),
        ),
    ]


@pytest.fixture
def sample_past_open_times():
    """Sample open/close times for events"""
    now = datetime.now(timezone.utc)
    return [
        OpenTimes(
            open_time=now + timedelta(days=-5, hours=1),
            close_time=now + timedelta(days=-5, hours=8),
        ),
        OpenTimes(
            open_time=now + timedelta(days=-4, hours=1),
            close_time=now + timedelta(days=-4, hours=8),
        ),
    ]


@pytest.fixture
def sample_future_event(sample_future_open_times):
    """Sample NewEvent data for testing"""
    return NewEvent(
        name="Test Event",
        slug="future-event",
        hostedBy="Test Host",
        hostedByUrl="https://example.com",
        seats=5,
        duration=3600,
        openTimes=sample_future_open_times,
    )


@pytest_asyncio.fixture
async def sample_current_event(db_session, sample_current_open_times):
    """Pre-created event in database"""
    event = Event(
        slug="current-event",
        name="Existing Event",
        createdBy="test_user",
        hostedBy="Test Host",
        hostedByUrl="https://example.com",
        seatDuration=3600,
    )

    for time_pair in sample_current_open_times:
        event.open_times.append(
            OpenTime(open_time=time_pair.open_time, close_time=time_pair.close_time)
        )

    event.seats = [Seat(seat_number=i) for i in range(1, 4)]

    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def sample_future_event(db_session, sample_future_open_times):
    """Pre-created event in database"""
    event = Event(
        slug="future-event",
        name="Existing Event",
        createdBy="test_user",
        hostedBy="Test Host",
        hostedByUrl="https://example.com",
        seatDuration=3600,
    )

    for time_pair in sample_future_open_times:
        event.open_times.append(
            OpenTime(open_time=time_pair.open_time, close_time=time_pair.close_time)
        )

    event.seats = [Seat(seat_number=i) for i in range(1, 4)]

    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def sample_past_event(db_session, sample_past_open_times):
    """Pre-created event in database"""
    event = Event(
        slug="existing-event",
        name="Existing Event",
        createdBy="test_user",
        hostedBy="Test Host",
        hostedByUrl="https://example.com",
        seatDuration=3600,
    )

    for time_pair in sample_past_open_times:
        event.open_times.append(
            OpenTime(open_time=time_pair.open_time, close_time=time_pair.close_time)
        )

    event.seats = [Seat(seat_number=i) for i in range(1, 4)]

    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def event_with_artists(sample_future_event, db_session):
    """Event with sample artists"""
    artist = Artist(
        event_id=sample_future_event.id, name="Test Artist", slug="test-artist"
    )
    db_session.add(artist)
    await db_session.commit()
    return sample_future_event


@pytest_asyncio.fixture
async def setup_events(sample_current_event, sample_future_event, sample_past_event):
    """Setup all event types for testing"""
    return {
        "current": sample_current_event,
        "future": sample_future_event,
        "past": sample_past_event,
    }


@pytest.mark.asyncio
async def test_list_events_empty(httpx_client: AsyncClient):
    """Test list events with no events"""
    response = await httpx_client.get("/event/list")
    assert response.status_code == 200
    data = response.json()
    assert data["current"] == []
    assert data["upcoming"] == []
    assert data["past"] == []


@pytest.mark.asyncio
async def test_list_events_categorizes_correctly(httpx_client: AsyncClient, setup_events):
    """Test events are categorized by date"""
    response = await httpx_client.get("/event/list")
    assert response.status_code == 200
    data = response.json()

    assert len(data["current"]) == 1
    assert len(data["upcoming"]) == 1
    assert len(data["past"]) == 1

    assert data["current"][0]["slug"] == "current-event"
    assert data["upcoming"][0]["slug"] == "future-event"
    assert data["past"][0]["slug"] == "existing-event"


@pytest.mark.asyncio
async def test_list_events_structure(httpx_client: AsyncClient, sample_current_event):
    """Test event structure in response"""
    response = await httpx_client.get("/event/list")
    assert response.status_code == 200
    data = response.json()

    event = data["current"][0]
    assert "name" in event
    assert "slug" in event
    assert "seats" in event
    assert "seatsAvailable" in event
    assert "open" in event
