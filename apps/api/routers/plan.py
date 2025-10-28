from fastapi import APIRouter
from ..core.schemas import Config, Plan
from packages.engines import llm as llm_engine

router = APIRouter(tags=["plan"])

@router.post("/plan", response_model=Plan)
async def make_plan(cfg: Config):
    words = cfg.length.value * cfg.voice.pace_wpm
    beats_total = cfg.length.value * cfg.structure.beats_per_min
    plan_dict = llm_engine.produce_plan(cfg.topic, beats_total, words, cfg)
    return Plan(**plan_dict)
