from typing import Annotated, Literal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from cctracker.event.core import EventManagementDetails, Spot, SpotList

router = APIRouter()


@router.put("/{event}")
async def create_event(
    event: str, details: EventManagementDetails
) -> EventManagementDetails:
    details.slug = event
    return details


@router.post("/{event}")
async def update_event(
    event: str, details: EventManagementDetails
) -> EventManagementDetails:
    if details.slug != event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Slug does not match"
        )
    return details


@router.get("/{event}")
async def get_event(event: str) -> EventManagementDetails:
    return EventManagementDetails()


class SpotQuery(BaseModel):
    spot: int | None = Field(None, gt=0)
    show: Literal["all", "active", "inactive"] = "active"


@router.get("/{event}/spots")
async def get_spots(event: str, query: Annotated[SpotQuery, Query()]) -> SpotList:
    return SpotList()


@router.post("/{event}/spots")
async def update_spotss(event: str, details: Spot, force: bool = False):
    pass
