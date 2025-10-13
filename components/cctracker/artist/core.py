from fastapi import APIRouter

router = APIRouter()

@router.get("/register")
async def register_artist(id: str | None):
    pass


@router.get("/{artist_id}")
async def get_artist(artist_id: str):
    pass

@router.post("/{artist_id}")
async def update_artist(artist_id: str):
    pass

@router.post("/{artist_id}/icon")
async def set_artist_icon(artist_id: str, g
