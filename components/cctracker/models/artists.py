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
    timeSinceLastAssignment: PositiveInt | None


class ArtistCustomizableDetails(BaseModel):
    name: str
    details: str
    eventId: str | None
    profileUrl: HttpUrl
    commissionsOpen: bool
    commissionsRemaining: PositiveInt


class ArtistCustomizableDetails_User(BaseModel):
    name: str
    details: str
    profileUrl: HttpUrl
    imageUrl: HttpUrl


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
