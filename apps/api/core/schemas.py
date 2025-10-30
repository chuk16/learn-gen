from pydantic import BaseModel
from typing import List, Literal, Optional, Dict, Any

class Length(BaseModel):
    unit: Literal["min"] = "min"
    value: int = 3

class Research(BaseModel):
    web_search: bool = False
    sources: List[str] = []

class Visuals(BaseModel):
    # Animation-first defaults; SDXL only if truly needed
    use_generated_images: Literal["auto","none","force"] = "auto"
    style: str = "kurzgesagt-flat-vector"
    fps: int = 30
    animation_mode: Literal["cinematic","infographic"] = "cinematic"

    # NEW: output format controls
    aspect: Literal["landscape","portrait","square"] = "landscape"
    # Height in pixels (the tall edge); width is derived from aspect
    target_height: int = 1080   # 1080p ? 1920x1080 (landscape) or 1080x1920 (portrait)

class Voice(BaseModel):
    # Pass an absolute path to Piper .onnx in the request or set it here
    speaker: str = "/workspace/learn-gen/voices/piper/en_US-norman-medium.onnx"
    pace_wpm: int = 145
    tone: str = "energetic"

class Structure(BaseModel):
    # Fewer, richer animated beats by default
    beats_per_min: int = 9
    cta: bool = False
    quizlets: int = 0

class Config(BaseModel):
    topic: str
    length: Length = Length()
    research: Research = Research()
    visuals: Visuals = Visuals()
    voice: Voice = Voice()
    structure: Structure = Structure()

class Onscreen(BaseModel):
    title: Optional[str] = None
    bullets: List[str] = []
    diagram: Optional[Dict[str, Any]] = None    # e.g., {"kind":"timeline"|"diagram"|"path", ...}
    anim_path: Optional[Dict[str, Any]] = None   # path parameters if any
    assets: Dict[str, Any] = {"need_image": False, "style": "kurzgesagt-flat-vector", "reference_terms": [], "subject": None}

class Beat(BaseModel):
    type: Literal["layout","diagram","timeline","anim_path"]
    narration: str
    onscreen: Onscreen = Onscreen()
    duration_s: float = 6.0

class Section(BaseModel):
    id: str
    goal: str
    beats: List[Beat]

class Plan(BaseModel):
    topic: str
    length_min: int
    sections: List[Section]
    narration_full: str
