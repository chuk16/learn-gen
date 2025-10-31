# packages/engines/anim.py
# Procedural clip generator tuned for vibrant, flat-vector Kurzgesagt-style visuals.

import hashlib
import math
import os
import random
import subprocess
import uuid
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ANIM_OUT = "data/anims"
FPS_DEFAULT = 30

# Try a system font; fall back to default
try:
    FONT_PATH = "arial.ttf"
    _ = ImageFont.truetype(FONT_PATH, 36)
except Exception:
    FONT_PATH = None

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS  # type: ignore[attr-defined]
except AttributeError:
    RESAMPLE_LANCZOS = Image.LANCZOS

# High-saturation palettes inspired by Kurzgesagt color design
PALETTES = (
    {
        "bg": ("#0F1C4D", "#1F4CBF"),
        "primary": "#FFB347",
        "secondary": "#4CD7F6",
        "accent": "#FF6B8C",
        "neutral": "#F5F7FF",
    },
    {
        "bg": ("#1A1040", "#3A2B8C"),
        "primary": "#FFD166",
        "secondary": "#63E6BE",
        "accent": "#FF6F61",
        "neutral": "#FAFBFF",
    },
    {
        "bg": ("#10273F", "#1E5F99"),
        "primary": "#FF9F1C",
        "secondary": "#6EE7FF",
        "accent": "#845EF7",
        "neutral": "#F1F5FF",
    },
    {
        "bg": ("#122B39", "#215372"),
        "primary": "#F4A261",
        "secondary": "#2DD4BF",
        "accent": "#FF5D8F",
        "neutral": "#F8FAFC",
    },
)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _font(size: int) -> ImageFont.FreeTypeFont:
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    """Return text width/height across Pillow versions."""
    if not text:
        return 0, 0
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
    except AttributeError:
        try:
            bbox = font.getbbox(text)  # type: ignore[attr-defined]
        except AttributeError:
            try:
                return font.getsize(text)  # type: ignore[attr-defined]
            except AttributeError:
                return draw.textsize(text, font=font)  # type: ignore[attr-defined]
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _mix(color: Tuple[int, int, int], target: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    factor = max(0.0, min(1.0, factor))
    return tuple(int(c * (1 - factor) + t * factor) for c, t in zip(color, target))


def _palette_for(seed: str) -> dict:
    idx = int(hashlib.sha1(seed.encode("utf-8")).hexdigest(), 16) % len(PALETTES)
    raw = PALETTES[idx]
    return {
        "bg": (_hex_to_rgb(raw["bg"][0]), _hex_to_rgb(raw["bg"][1])),
        "primary": _hex_to_rgb(raw["primary"]),
        "secondary": _hex_to_rgb(raw["secondary"]),
        "accent": _hex_to_rgb(raw["accent"]),
        "neutral": _hex_to_rgb(raw["neutral"]),
    }


def _vertical_gradient(size: Tuple[int, int], top: Tuple[int, int, int], bottom: Tuple[int, int, int]) -> Image.Image:
    width, height = size
    base = Image.new("RGB", (width, height), top)
    mask = Image.new("L", (1, height))
    for y in range(height):
        mask.putpixel((0, y), int(255 * (y / max(1, height - 1))))
    mask = mask.resize((width, height))
    overlay = Image.new("RGB", (width, height), bottom)
    return Image.composite(overlay, base, mask)


def _build_background(width: int, height: int, palette: dict, rng: random.Random) -> Image.Image:
    grad = _vertical_gradient((width, height), palette["bg"][0], palette["bg"][1]).convert("RGBA")

    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    radius = int(min(width, height) * rng.uniform(0.65, 0.9))
    cx = int(width * rng.uniform(0.35, 0.65))
    cy = int(height * rng.uniform(0.18, 0.42))
    glow_draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=palette["secondary"] + (90,),
    )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=int(min(width, height) * 0.27)))
    combined = Image.alpha_composite(grad, glow_layer)

    grain = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grain_draw = ImageDraw.Draw(grain)
    dot_count = int(width * height * 0.0025)
    for _ in range(dot_count):
        x = rng.randrange(width)
        y = rng.randrange(height)
        alpha = rng.randint(10, 24)
        grain_draw.point((x, y), fill=palette["neutral"] + (alpha,))
    grain = grain.filter(ImageFilter.GaussianBlur(radius=1))

    return Image.alpha_composite(combined, grain)


def _apply_background_image(base: Image.Image, width: int, height: int, palette: dict, path: Optional[str]) -> Image.Image:
    if not path:
        return base
    try:
        bg = Image.open(path).convert("RGBA")
        bg = ImageOps.fit(bg, (width, height), method=RESAMPLE_LANCZOS)
        tint = Image.new("RGBA", (width, height), palette["bg"][0] + (70,))
        bg = Image.alpha_composite(bg, tint)
        merged = Image.blend(bg, base, alpha=0.4)
        return merged
    except Exception:
        return base


def _make_star_field(width: int, height: int, rng: random.Random, palette: dict) -> Image.Image:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    count = int(width * height * 0.00014)
    for _ in range(count):
        x = rng.randrange(width)
        y = rng.randrange(height)
        size = rng.randint(1, 3)
        alpha = rng.randint(90, 150)
        draw.ellipse((x, y, x + size, y + size), fill=palette["neutral"] + (alpha,))
    return layer


def _draw_title(img: Image.Image, title: str, palette: dict) -> None:
    if not title:
        return
    draw = ImageDraw.Draw(img)
    font = _font(max(48, img.width // 18))
    tw, th = _measure_text(draw, title, font)
    x = (img.width - tw) // 2
    y = int(img.height * 0.08)
    draw.text((x + 4, y + 4), title, fill=palette["accent"], font=font)
    draw.text((x, y), title, fill=palette["neutral"], font=font)


def _draw_bullets(img: Image.Image, bullets: List[str], palette: dict) -> Image.Image:
    if not bullets:
        return img
    result = img
    margin = int(min(img.width, img.height) * 0.08)
    pill_height = int(img.height * 0.08)
    line_gap = int(img.height * 0.105)
    font_size = max(28, img.width // 42)
    for idx, bullet in enumerate(bullets[:4]):
        top = int(img.height * 0.26) + idx * line_gap
        rect = (
            margin,
            top,
            img.width - margin,
            top + pill_height,
        )
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(rect, radius=pill_height // 2, fill=(0, 0, 0, 70))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=6))
        result = Image.alpha_composite(result, shadow)

        pill_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        pill_draw = ImageDraw.Draw(pill_layer)
        pill_draw.rounded_rectangle(rect, radius=pill_height // 2, fill=palette["primary"] + (235,))
        result = Image.alpha_composite(result, pill_layer)

        draw = ImageDraw.Draw(result)
        text_x = rect[0] + int(pill_height * 0.55)
        text_y = rect[1] + int(pill_height * 0.2)
        draw.text((text_x, text_y), f"> {bullet}", fill=palette["neutral"], font=_font(font_size))
    return result


def _draw_reference_badge(img: Image.Image, references: List[str], palette: dict) -> Image.Image:
    if not references:
        return img
    text = " / ".join(references[:2])
    font = _font(max(20, img.width // 60))
    draw = ImageDraw.Draw(img)
    tw, th = _measure_text(draw, text, font)
    pad = int(img.height * 0.02)
    margin = int(img.width * 0.05)
    x0 = margin
    y1 = img.height - margin
    y0 = max(margin, y1 - th - pad * 2)
    badge_rect = (x0, y0, x0 + tw + pad * 2, y1)

    badge_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge_layer)
    badge_draw.rounded_rectangle(badge_rect, radius=max(12, int(th * 0.6)), fill=palette["accent"] + (215,))
    badge_layer = badge_layer.filter(ImageFilter.GaussianBlur(radius=2))
    img = Image.alpha_composite(img, badge_layer)

    draw = ImageDraw.Draw(img)
    draw.text((x0 + pad, y0 + pad // 2), text, fill=palette["neutral"], font=font)
    return img


def _encode_frames_to_mp4(frames_dir: str, fps: int, out_path: str) -> str:
    cmd = [
        "ffmpeg",
        "-y",
        "-r",
        str(fps),
        "-f",
        "image2",
        "-i",
        os.path.join(frames_dir, "%06d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        f"fps={fps}",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path


def _render_timeline(
    background: Image.Image,
    palette: dict,
    title: str,
    items: List[str],
    nframes: int,
    references: List[str],
) -> List[Image.Image]:
    frames: List[Image.Image] = []
    width, height = background.size
    line_y = int(height * 0.58)
    left = int(width * 0.1)
    right = int(width * 0.9)
    radius = max(12, width // 140)

    for frame_idx in range(nframes):
        img = background.copy()
        _draw_title(img, title, palette)

        glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_alpha = int(70 + 40 * (0.5 + 0.5 * math.sin(2 * math.pi * frame_idx / nframes)))
        glow_draw.line((left, line_y, right, line_y), fill=palette["secondary"] + (glow_alpha,), width=max(8, width // 160))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=4))
        img = Image.alpha_composite(img, glow_layer)

        draw = ImageDraw.Draw(img)
        draw.line((left, line_y, right, line_y), fill=palette["secondary"], width=max(4, width // 210))

        for idx, label in enumerate(items):
            reveal = int(((idx + 1) / (len(items) + 1)) * nframes)
            x = int(left + idx * (right - left) / max(1, len(items) - 1))
            base_color = palette["accent"] if frame_idx >= reveal else _mix(palette["accent"], palette["bg"][0], 0.55)

            pulse_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            pulse_draw = ImageDraw.Draw(pulse_layer)
            pulse_draw.ellipse(
                (x - radius * 2, line_y - radius * 2, x + radius * 2, line_y + radius * 2),
                fill=palette["accent"] + (90,),
            )
            pulse_layer = pulse_layer.filter(ImageFilter.GaussianBlur(radius=4))
            img = Image.alpha_composite(img, pulse_layer)

        draw.ellipse((x - radius, line_y - radius, x + radius, line_y + radius), fill=base_color)

        if frame_idx >= reveal:
            label_font = _font(max(24, width // 46))
            tw, th = _measure_text(draw, label, label_font)
            rect = (
                x - tw // 2 - 16,
                line_y - radius - th - 20,
                x + tw // 2 + 16,
                line_y - radius - 12,
            )
            tag_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            tag_draw = ImageDraw.Draw(tag_layer)
            tag_draw.rounded_rectangle(rect, radius=14, fill=palette["primary"] + (235,))
            tag_layer = tag_layer.filter(ImageFilter.GaussianBlur(radius=1))
            img = Image.alpha_composite(img, tag_layer)
            draw.text((x - tw // 2, rect[1] + 4), label, fill=palette["neutral"], font=label_font)

        img = _draw_reference_badge(img, references, palette)
        frames.append(img.convert("RGB"))
    return frames


def _render_path(
    background: Image.Image,
    palette: dict,
    title: str,
    nframes: int,
    star_field: Image.Image,
    references: List[str],
) -> List[Image.Image]:
    frames: List[Image.Image] = []
    width, height = background.size
    center_x, center_y = width // 2, height // 2
    hole_radius = int(min(width, height) * 0.09)

    for frame_idx in range(nframes):
        t = frame_idx / max(1, nframes - 1)
        eased = 0.5 - 0.5 * math.cos(math.pi * t)
        img = background.copy()
        if star_field:
            img = Image.alpha_composite(img, star_field)
        _draw_title(img, title, palette)

        target_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        target_draw = ImageDraw.Draw(target_layer)
        rim = hole_radius * 2
        target_draw.ellipse(
            (center_x - rim, center_y - rim, center_x + rim, center_y + rim),
            outline=palette["secondary"] + (220,),
            width=max(4, width // 230),
        )
        target_draw.ellipse(
            (center_x - hole_radius, center_y - hole_radius, center_x + hole_radius, center_y + hole_radius),
            fill=(8, 12, 20, 255),
        )
        target_layer = target_layer.filter(ImageFilter.GaussianBlur(radius=2))
        img = Image.alpha_composite(img, target_layer)

        start_x = int(width * 0.1)
        start_y = int(height * 0.8)
        control_x = int(width * 0.55)
        control_y = int(height * 0.35)

        trail_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        trail_draw = ImageDraw.Draw(trail_layer)
        steps = 120
        path_points = []
        for step in range(steps + 1):
            tt = eased * (step / steps)
            px = int((1 - tt) ** 2 * start_x + 2 * (1 - tt) * tt * control_x + tt ** 2 * center_x)
            py = int((1 - tt) ** 2 * start_y + 2 * (1 - tt) * tt * control_y + tt ** 2 * center_y)
            path_points.append((px, py))
        if len(path_points) > 1:
            trail_draw.line(path_points, fill=palette["secondary"] + (210,), width=max(6, width // 220))
        trail_layer = trail_layer.filter(ImageFilter.GaussianBlur(radius=2))
        img = Image.alpha_composite(img, trail_layer)

        current_x, current_y = path_points[-1]
        ship_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ship_draw = ImageDraw.Draw(ship_layer)
        ship_size = max(18, width // 58)
        fin_height = int(ship_size / 1.7)
        ship = [
            (current_x + ship_size, current_y),
            (current_x - ship_size, current_y - fin_height),
            (current_x - ship_size, current_y + fin_height),
        ]
        ship_draw.polygon(ship, fill=palette["accent"] + (245,))
        flame = [
            (current_x - ship_size, current_y - fin_height // 2),
            (current_x - ship_size - int(ship_size * 0.9), current_y),
            (current_x - ship_size, current_y + fin_height // 2),
        ]
        ship_draw.polygon(flame, fill=palette["primary"] + (220,))
        ship_layer = ship_layer.filter(ImageFilter.GaussianBlur(radius=0.8))
        img = Image.alpha_composite(img, ship_layer)

        img = _draw_reference_badge(img, references, palette)
        frames.append(img.convert("RGB"))
    return frames


def _render_diagram(
    background: Image.Image,
    palette: dict,
    title: str,
    bullets: List[str],
    nframes: int,
    references: List[str],
) -> List[Image.Image]:
    frames: List[Image.Image] = []
    width, height = background.size
    margin = int(min(width, height) * 0.08)
    card_rect = (
        margin,
        int(margin * 1.35),
        width - margin,
        height - int(margin * 1.1),
    )
    card_radius = int(min(width, height) * 0.04)
    card_width = card_rect[2] - card_rect[0]
    card_height = card_rect[3] - card_rect[1]

    top_color = _mix(palette["primary"], palette["neutral"], 0.35)
    bottom_color = _mix(palette["secondary"], palette["neutral"], 0.55)
    card_base = _vertical_gradient((card_width, card_height), top_color, bottom_color).convert("RGBA")
    card_base.putalpha(235)

    grid_layer = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_layer)
    step = max(24, card_width // 18)
    grid_color = palette["neutral"] + (36,)
    for gx in range(0, card_width, step):
        grid_draw.line((gx, 0, gx, card_height), fill=grid_color, width=1)
    for gy in range(0, card_height, step):
        grid_draw.line((0, gy, card_width, gy), fill=grid_color, width=1)
    grid_layer = grid_layer.filter(ImageFilter.GaussianBlur(radius=1))

    for frame_idx in range(nframes):
        img = background.copy()
        _draw_title(img, title, palette)

        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(card_rect, radius=card_radius, fill=(0, 0, 0, 80))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
        img = Image.alpha_composite(img, shadow)

        img.paste(card_base, (card_rect[0], card_rect[1]), card_base)

        highlight = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        highlight_draw = ImageDraw.Draw(highlight)
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * frame_idx / nframes)
        hx = card_width // 2
        hy = int(card_height * 0.35)
        radius = int(card_width * (0.45 + 0.1 * pulse))
        highlight_draw.ellipse(
            (hx - radius, hy - radius, hx + radius, hy + radius),
            fill=palette["neutral"] + (int(55 + 30 * pulse),),
        )
        highlight = highlight.filter(ImageFilter.GaussianBlur(radius=18))
        img.paste(highlight, (card_rect[0], card_rect[1]), highlight)

        img.paste(grid_layer, (card_rect[0], card_rect[1]), grid_layer)
        img = _draw_bullets(img, bullets, palette)
        img = _draw_reference_badge(img, references, palette)
        frames.append(img.convert("RGB"))
    return frames


def render(
    spec: dict,
    duration_s: float = 6.0,
    title: str = "",
    bullets: Optional[List[str]] = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = FPS_DEFAULT,
) -> str:
    """Render a short MP4 clip with vibrant flat-vector styling."""
    bullets = bullets or []
    kind = (spec.get("diagram", {}) or {}).get("kind") or spec.get("kind") or "diagram"
    subject = spec.get("subject") or title or kind
    references = spec.get("references", []) or []

    _ensure_dir(ANIM_OUT)
    out_path = os.path.join(ANIM_OUT, f"{kind}_{uuid.uuid4().hex}.mp4")

    nframes = max(1, int(fps * duration_s))
    frames_dir = os.path.join(ANIM_OUT, f"frames_{uuid.uuid4().hex}")
    _ensure_dir(frames_dir)

    seed_key = subject or f"{title or kind}-{kind}"
    seed_value = int(hashlib.sha1(seed_key.encode("utf-8")).hexdigest(), 16)
    palette = _palette_for(seed_key)
    background = _build_background(width, height, palette, random.Random(seed_value ^ 0x1234))
    background = _apply_background_image(background, width, height, palette, spec.get("background_image"))

    if kind == "timeline":
        items = spec.get("items", ["Act I", "Act II", "Act III"])
        frames = _render_timeline(background, palette, title, items, nframes, references)
    elif kind == "path":
        star_layer = _make_star_field(width, height, random.Random(seed_value ^ 0x9ABC), palette)
        frames = _render_path(background, palette, title, nframes, star_layer, references)
    else:
        frames = _render_diagram(background, palette, title, bullets, nframes, references)

    for idx, frame in enumerate(frames):
        frame.save(os.path.join(frames_dir, f"{idx:06d}.png"))

    return _encode_frames_to_mp4(frames_dir, fps, out_path)
