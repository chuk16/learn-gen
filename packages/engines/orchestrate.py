import json
import os
from pathlib import Path
from typing import List, Tuple
from . import llm, tts, captions, anim, render
import soundfile as sf

DEBUG_DIR = "data/debug"


def _flatten_beats(plan) -> List[tuple]:
    beats = []
    for sec in plan.get("sections", []):
        for b in sec.get("beats", []):
            beats.append((sec, b))
    return beats


def _dims(aspect: str, target_height: int) -> Tuple[int, int]:
    if aspect == "portrait":
        w = int(round(target_height * 9 / 16))
        return (w, target_height)
    if aspect == "square":
        return (target_height, target_height)
    w = int(round(target_height * 16 / 9))
    return (w, target_height)


def _compose_narration(plan: dict) -> str:
    parts = []
    topic = plan.get("topic") or ""
    if topic:
        parts.append(f"{topic}.")
    for sec in plan.get("sections", []):
        sec_id = sec.get("id")
        if sec_id:
            parts.append(sec_id.replace("_", " ").title() + ":")
        for b in sec.get("beats", []):
            n = (b.get("narration") or "").strip()
            if n:
                parts.append(n)
    text = " ".join(parts).strip()
    return text or "Here is a short explainer."


def _should_ignore_narration(narration: str) -> bool:
    if not narration:
        return True
    words = narration.strip().split()
    if len(words) < 8:
        return True
    lowered = narration.lower()
    if "test video" in lowered or "placeholder" in lowered:
        return True
    return False


async def run(cfg):
    words = cfg.length.value * cfg.voice.pace_wpm
    beats_target = cfg.length.value * cfg.structure.beats_per_min

    plan = llm.produce_plan(cfg.topic, beats_target, words, cfg)

    try:
        Path(DEBUG_DIR).mkdir(parents=True, exist_ok=True)
        with open(Path(DEBUG_DIR) / "latest_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # --- dimensions & fps from config ---
    aspect = getattr(cfg.visuals, "aspect", "landscape")
    target_h = getattr(cfg.visuals, "target_height", 1080)
    W, H = _dims(aspect, target_h)
    FPS = getattr(cfg.visuals, "fps", 30)

    # 1) Voice + captions first
    narration_raw = (plan.get("narration_full") or "").strip()
    if _should_ignore_narration(narration_raw):
        narration = _compose_narration(plan)
    else:
        narration = narration_raw
    wav = tts.synthesize(narration, cfg.voice.speaker)
    dur_s = sf.info(wav).duration if os.path.exists(wav) else (cfg.length.value * 60)
    srt = captions.to_srt(wav)

    # 2) Build animations per beat
    flattened = _flatten_beats(plan)
    n = max(1, len(flattened))
    per = max(4.0, dur_s / n)

    clips = []
    if flattened:
        for sec, b in flattened:
            btype = b.get("type")
            ons = b.get("onscreen", {}) or {}
            title = ons.get("title") or sec.get("id") or cfg.topic
            bullets = ons.get("bullets", [])
            assets = ons.get("assets", {}) or {}
            subject = assets.get("subject") or title
            references = assets.get("reference_terms") or []
            spec_style = assets.get("style") or "kurzgesagt-flat-vector"
            spec = {"kind": "diagram"}
            if btype == "timeline":
                spec = {"kind": "timeline", "items": bullets or ["Act I", "Act II", "Act III"]}
            elif btype == "anim_path":
                spec = {"kind": "path", "anim_path": ons.get("anim_path", {"duration": per})}
            elif btype == "diagram":
                spec = {"kind": "diagram", "title": title}
            spec["style"] = spec_style
            spec["subject"] = subject
            if references:
                spec["references"] = references
            # layout -> diagram fallback with title/bullets
            clip = anim.render(spec, per, title, bullets, width=W, height=H, fps=FPS)
            clips.append(clip)
    else:
        # Fallback: single title/diagram clip covering the whole narration duration
        title = (plan.get("topic") or cfg.topic)
        spec = {"kind": "diagram", "title": title, "style": "kurzgesagt-flat-vector", "subject": title}
        clip = anim.render(spec, max(6.0, dur_s), title, [], width=W, height=H, fps=FPS)
        clips.append(clip)

    # 3) Compose final (concat -> add VO + subs) -- compose will also guard empty lists
    out_name = f"{cfg.topic[:48].replace(' ', '_')}.mp4"
    mp4 = render.compose(clips, wav, srt, fps=FPS, out_name=out_name)

    return {
        "plan": plan,
        "assets": {"clips": clips, "wav": wav, "srt": srt},
        "final_mp4": mp4,
    }
