from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status, Security
from fastapi.security import OAuth2AuthorizationCodeBearer, SecurityScopes
from pydantic import BaseModel, Field

from cctracker.event.core import EventManagementDetails, Spot, SpotList, oauth2_scheme

router = APIRouter()


@router.put("/")
async def create_event(
    details: EventManagementDetails,
    user: Annotated[get_current_user].
    token: Annotated[
        OAuth2AuthorizationCodeBearer,
        Security(oauth2_scheme, scopes=["event:create", "event:admin"]),
    ],
    security_scopes: SecurityScopes,
) -> EventManagementDetails:
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
