from pydantic import BaseModel, HttpUrl, PositiveInt


class Artist(BaseModel):
    name: str
    slug: str
    eventId: str
    details: str  # Profile details
    imageUrl: str  # Profile Picture
    profileUrl: str  # External Profile (linktree or store)
    commissionsOpen: bool
    commissionsRemaining: PositiveInt
    active: bool
    timeRemaining: PositiveInt | None


class ArtistCustomizableDetails(BaseModel):
    name: str
    details: str
    eventId: str
    profileUrl: HttpUrl
    commissionsOpen: bool
    commissionsRemaining: PositiveInt


class ArtistSummary(BaseModel):
    name: str
    slug: str
    eventId: str
    imageUrl: str
    seat: PositiveInt

class RequestNewArtist(BaseModel):
    name: str
    slug: str
    eventId: str
    seat: PositiveInt | None
