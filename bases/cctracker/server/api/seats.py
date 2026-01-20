from fastapi import APIRouter

api_router = APIRouter(prefix="/event", tags=["Event Seat Operations"])


@api_router.get("/{eventId}/seats")
async def get_event_seats(eventId: str):
    pass


@api_router.delete("/{eventId}/seats")
async def end_all_assignments(eventId: str):
    pass


@api_router.get("/{eventId}/seat/{seatNumber}")
async def get_event_seat(eventId: str, seatNumber: int):
    pass


@api_router.delete("/{eventId}/seat/{seatNumber}")
async def end_assignment_at_seat(eventId: str, seatNumber: int):
    pass
