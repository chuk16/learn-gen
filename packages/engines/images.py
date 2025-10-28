# packages/engines/images.py
# Lazy SDXL loader so the API doesn't crash if diffusers/torchvision aren't installed.
# Only import diffusers when get_pipe() is actually called.

import os
import torch

_pipe = None
OUT = "data/frames"


def get_pipe():
    """
    Returns a cached SDXL pipeline. Imports diffusers only on demand.
    Raises a helpful error if diffusers/vision deps are missing.
    """
    global _pipe
    if _pipe:
        return _pipe

    try:
        from diffusers import StableDiffusionXLPipeline  # lazy import
    except Exception as e:
        raise RuntimeError(
            "Image engine unavailable. To enable SDXL, install the vision deps:\n"
            '  python -m pip install "transformers[vision]" diffusers\n'
            "…or keep visuals.use_generated_images='none' to skip images."
        ) from e

    _pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        use_safetensors=True,
    )
    _pipe = _pipe.to("cuda" if torch.cuda.is_available() else "cpu")
    # Memory savers for smaller GPUs
    try:
        _pipe.enable_attention_slicing()
    except Exception:
        pass
    return _pipe


def render(
    pipe,
    prompt: str,
    index: int = 0,
    size: int = 768,
    steps: int = 30,
    cfg: float = 6.5,
    seed: int = 1234,
):
    """
    Render a single square SDXL image and save to data/frames/beat_XXX.png
    """
    g = torch.Generator(device=pipe.device).manual_seed(seed + index)
    result = pipe(
        prompt=prompt,
        height=size,
        width=size,
        num_inference_steps=steps,
        guidance_scale=cfg,
        generator=g,
    )
    img = result.images[0]
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"beat_{index:03}.png")
    img.save(path)
    return path
