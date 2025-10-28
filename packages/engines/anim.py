# packages/engines/anim.py
# Procedural clip generator (timeline / path / diagram) with arbitrary width/height (landscape/portrait/square)

import os, uuid, subprocess
from PIL import Image, ImageDraw, ImageFont

ANIM_OUT = "data/anims"
FPS_DEFAULT = 30

# Try a system font; fall back to default
try:
    FONT_PATH = "arial.ttf"
    _ = ImageFont.truetype(FONT_PATH, 36)
except Exception:
    FONT_PATH = None

def _ensure_dir(p): os.makedirs(p, exist_ok=True)

def _font(size):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()

def _encode_frames_to_mp4(frames_dir: str, fps: int, out_path: str):
    cmd = [
        "ffmpeg","-y","-r", str(fps),
        "-f","image2","-i", os.path.join(frames_dir, "%06d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p","-vf", f"fps={fps}",
        out_path
    ]
    subprocess.run(cmd, check=True)
    return out_path

def _draw_text(draw, text, xy, size=36, fill=(255,255,255)):
    draw.text(xy, text, fill=fill, font=_font(size))

def render(
    spec: dict,
    duration_s: float = 6.0,
    title: str = "",
    bullets=None,
    width: int = 1920,
    height: int = 1080,
    fps: int = FPS_DEFAULT
) -> str:
    """
    Render a short MP4 at (width x height).
    spec.kind ∈ {timeline, path, diagram}
    """
    bullets = bullets or []
    kind = (spec.get("diagram",{}) or {}).get("kind") or spec.get("kind") or "diagram"

    _ensure_dir(ANIM_OUT)
    out = os.path.join(ANIM_OUT, f"{kind}_{uuid.uuid4().hex}.mp4")

    nframes = max(1, int(fps * duration_s))
    frames_dir = os.path.join(ANIM_OUT, f"frames_{uuid.uuid4().hex}")
    _ensure_dir(frames_dir)

    cx, cy = width // 2, height // 2

    def save(i, img):
        img.save(os.path.join(frames_dir, f"{i:06d}.png"))

    # --- TIMELINE ---
    if kind == "timeline":
        items = spec.get("items", ["Setup","Inciting","Act II","Climax","Resolution"])
        y_line = int(height * 0.55)
        left, right = int(width*0.08), int(width*0.92)
        for i in range(nframes):
            img = Image.new("RGB", (width,height), (8,8,12))
            d = ImageDraw.Draw(img)
            d.line((left, y_line, right, y_line), fill=(180,180,180), width=max(3, width//640))
            for idx, label in enumerate(items):
                t_reveal = int(((idx+1)/(len(items)+1))*nframes)
                x = int(left + idx * (right-left)/max(1,len(items)-1))
                color = (230,230,230) if i >= t_reveal else (120,120,120)
                r = max(6, width//200)
                d.ellipse((x-r, y_line-r, x+r, y_line+r), fill=color)
                if i >= t_reveal:
                    _draw_text(d, str(label), (x-80, y_line-48), size=max(24, width//80))
            if title:
                _draw_text(d, title, (cx - len(title)*int(width*0.009), int(height*0.08)), size=max(40, width//48))
            save(i, img)
        return _encode_frames_to_mp4(frames_dir, fps, out)

    # --- PATH (spaceship toward black hole) ---
    if kind == "path":
        for i in range(nframes):
            t = i / max(1,nframes-1)
            img = Image.new("RGB", (width,height), (6,6,10))
            d = ImageDraw.Draw(img)
            # black hole
            R = max(40, min(width,height)//22)
            d.ellipse((cx-R, cy-R, cx+R, cy+R), outline=(220,220,220), width=max(2, width//960))
            d.ellipse((cx-R//3, cy-R//3, cx+R//3, cy+R//3), fill=(0,0,0))
            # simple quadratic bezier toward center
            x = int((1-t)**2 * int(width*0.08) + 2*(1-t)*t * int(width*0.5) + t*t * int(width*0.55))
            y = int((1-t)**2 * int(height*0.85) + 2*(1-t)*t * int(height*0.65) + t*t * int(height*0.5))
            s = max(12, min(width,height)//120)
            p1 = (x, y-s); p2 = (x-s, y+s); p3 = (x+s, y+s)
            d.polygon([p1,p2,p3], fill=(240,240,240))
            if title:
                _draw_text(d, title, (cx - len(title)*int(width*0.009), int(height*0.08)), size=max(40, width//48))
            save(i, img)
        return _encode_frames_to_mp4(frames_dir, fps, out)

    # --- DIAGRAM (default) ---
    for i in range(nframes):
        img = Image.new("RGB", (width,height), (10,10,14))
        d = ImageDraw.Draw(img)
        if title:
            _draw_text(d, title, (cx - len(title)*int(width*0.009), int(height*0.08)), size=max(40, width//48))
        # content box
        margin = int(min(width,height)*0.08)
        d.rounded_rectangle((margin, margin*1.4, width-margin, height-margin*1.8),
                            radius=int(min(width,height)*0.02), outline=(200,200,200),
                            width=max(2, width//960))
        # bullets
        for b_idx, b in enumerate(bullets[:4]):
            _draw_text(d, f"• {b}", (margin+20, int(height*0.22)+b_idx*int(height*0.06)),
                       size=max(28, width//68), fill=(230,230,230))
        save(i, img)
    return _encode_frames_to_mp4(frames_dir, fps, out)
