from fastapi import APIRouter
from ..core.schemas import Config
from packages.engines import orchestrate

router = APIRouter(tags=["generate"])

@router.post("/generate")
async def generate(cfg: Config):
    result = await orchestrate.run(cfg)
    return result  # {"plan":..., "assets": {...}, "final_mp4": "..."}
