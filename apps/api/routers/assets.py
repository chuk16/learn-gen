# apps/api/routers/assets.py
# Assets endpoints with LAZY image engine import.
# We only import the images module inside the /images route so the API runs fine
# when visuals.use_generated_images="none" and diffusers/torchvision are not installed.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from packages.engines import tts, captions, anim  # note: images is NOT imported here

router = APIRouter(tags=["assets"])


# ---------- Images ----------

class ImageTask(BaseModel):
    prompt: str
    size: int = 768
    seed: int = 42


@router.post("/images")
async def make_images(tasks: List[ImageTask]):
    # Lazy import so the server doesn't load diffusers unless we actually call this route.
    try:
        from packages.engines import images
        pipe = images.get_pipe()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Image engine unavailable: {e}")

    out_paths = []
    for i, t in enumerate(tasks):
        p = images.render(pipe, t.prompt, index=i, size=t.size, seed=t.seed)
        out_paths.append(p)
    return {"paths": out_paths}


# ---------- Voice (TTS) ----------

class TTSTask(BaseModel):
    text: str
    model_path: str  # absolute path to your Piper .onnx voice file


@router.post("/voice")
async def voice(task: TTSTask):
    return {"wav": tts.synthesize(task.text, task.model_path)}


# ---------- Captions (Whisper) ----------

@router.post("/captions")
async def caps(wav: str):
    return {"srt": captions.to_srt(wav)}


# ---------- Procedural animation clip ----------

class AnimTask(BaseModel):
    spec: dict
    duration_s: float = 6.0
    title: str = ""
    bullets: List[str] = []


@router.post("/anim")
async def make_anim(task: AnimTask):
    return {"mp4": anim.render(task.spec, task.duration_s, task.title, task.bullets)}
