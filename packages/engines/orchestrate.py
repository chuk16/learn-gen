import os
from typing import List, Tuple
from . import llm, tts, captions, anim, render
import soundfile as sf

def _flatten_beats(plan) -> List[dict]:
    beats = []
    for sec in plan["sections"]:
        for b in sec["beats"]:
            beats.append((sec, b))
    return beats

def _dims(aspect: str, target_height: int) -> Tuple[int,int]:
    """
    Returns (W,H) given aspect & target_height (tall edge).
    - landscape: 16:9 → (16/9 * H, H)
    - portrait:  9:16 → (9/16 * H, H)
    - square:    1:1  → (H, H)
    Width is snapped to integer; H is exactly target_height.
    """
    if aspect == "portrait":
        w = int(round(target_height * 9/16))
        return (w, target_height)            # e.g., 1080x1920 → pass H=1920
    if aspect == "square":
        return (target_height, target_height)
    # landscape default
    w = int(round(target_height * 16/9))
    return (w, target_height)                # e.g., 1920x1080 → pass H=1080

async def run(cfg):
    words = cfg.length.value * cfg.voice.pace_wpm
    beats_target = cfg.length.value * cfg.structure.beats_per_min
    plan = llm.produce_plan(cfg.topic, beats_target, words, cfg)

    # --- dimensions & fps from config ---
    aspect = getattr(cfg.visuals, "aspect", "landscape")
    target_h = getattr(cfg.visuals, "target_height", 1080)
    W, H = _dims(aspect, target_h)
    FPS = getattr(cfg.visuals, "fps", 30)

    # 1) Voice + captions first (know total duration)
    wav = tts.synthesize(plan["narration_full"], cfg.voice.speaker)
    dur_s = sf.info(wav).duration if os.path.exists(wav) else (cfg.length.value * 60)
    srt = captions.to_srt(wav)

    # 2) Build animations per beat (even allocation for now)
    flattened = _flatten_beats(plan)
    n = max(1, len(flattened))
    per = max(4.0, dur_s / n)

    clips = []
    for sec, b in flattened:
        btype = b.get("type")
        ons = b.get("onscreen", {}) or {}
        title = ons.get("title") or sec.get("id") or cfg.topic
        bullets = ons.get("bullets", [])
        spec = {"kind": "diagram"}
        if btype == "timeline":
            spec = {"kind": "timeline", "items": bullets or ["Act I","Act II","Act III"]}
        elif btype == "anim_path":
            spec = {"kind": "path", "anim_path": ons.get("anim_path", {"duration": per})}
        elif btype == "diagram":
            spec = {"kind": "diagram", "title": title}
        # layout -> diagram fallback with title/bullets
        clip = anim.render(spec, per, title, bullets, width=W, height=H, fps=FPS)
        clips.append(clip)

    # 3) Compose final (concat → add VO + subs)
    out_name = f"{cfg.topic[:48].replace(' ','_')}.mp4"
    mp4 = render.compose(clips, wav, srt, fps=FPS, out_name=out_name)

    return {"plan": plan, "assets": {"clips": clips, "wav": wav, "srt": srt}, "final_mp4": mp4}
