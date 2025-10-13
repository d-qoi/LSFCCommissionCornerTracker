from fastapi import APIRouter

from cctracker.event.core import EventDetails

router = APIRouter()


@router.get("/{event}")
async def details(event: str) -> EventDetails:
    return EventDetails()


@router.post("/{event}/subscribe")
async def subscribe(event: str):
    return True
