from fastapi import APIRouter


router = APIRouter()

@router.post("{event}/artist/register")
async def register_artist(event: str):
    pass

@router.get("/{event}/artist/{artist}")
async def get_artist_details(event: str, artist: str):
    pass


@router.post("/{event}/artist/{artist}")
async def set_artist_details(event: str, artist: str):
    pass


@router.post("/{event}/artist/{artist}/store")
async def save_or_load_artist(event: str, artist: str):
    pass
