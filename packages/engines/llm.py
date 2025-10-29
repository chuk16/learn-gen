import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Choose a size that fits your box; switch to 7B on a 24GB GPU.
MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

_tok = None
_mdl = None


def _safe_device_kwargs():
    use_cuda = torch.cuda.is_available()
    return {
        "device_map": "auto" if use_cuda else "cpu",
        "torch_dtype": torch.float16 if use_cuda else torch.float32,
        "low_cpu_mem_usage": True,
    }


def _load():
    global _tok, _mdl
    if _mdl is not None:
        return _tok, _mdl
    _tok = AutoTokenizer.from_pretrained(MODEL, use_fast=True)
    _mdl = AutoModelForCausalLM.from_pretrained(MODEL, **_safe_device_kwargs())
    return _tok, _mdl


# ---------------------- Prompting ----------------------

SYS = (
    "YouOUTPUTSTRICTJSON. Return ONLY a single JSON object with the exact fields asked. "
    "No markdown, no code fences, no commentary. "
    "Primary medium is procedural animation (timelines/diagrams/path); avoid photoreal faces."
)

JSON_SHAPE = """Your JSON MUST have:
{
  "topic": string,
  "length_min": number,
  "narration_full": string,
  "sections": [
    {
      "id": string,
      "goal": string,
      "beats": [
        {
          "type": "layout"|"diagram"|"timeline"|"anim_path",
          "narration": string,
          "onscreen": {
            "title": string|null,
            "bullets": string[],
            "diagram": object|null,
            "anim_path": object|null,
            "assets": object
          },
          "duration_s": number
        }
      ]
    }
  ]
}
Constraints: max 2 sentences per beat; include a pattern break roughly every 15–20 seconds.
"""


# ---------------------- (Optional) RAG / web search ----------------------

def _maybe_build_context(topic, cfg):
    try:
        if not getattr(cfg.research, "web_search", False):
            return None
    except Exception:
        return None
    try:
        from . import research
    except Exception:
        return None

    extra_urls = getattr(cfg.research, "sources", []) or []
    bundle = research.gather(topic, extra_urls=extra_urls)
    if not bundle or not bundle.get("chunks"):
        return None

    lines = [f"[{ch['source_id']}] {ch['text']}" for ch in bundle["chunks"]]
    ctx = "\n".join(lines)
    return {"context": ctx, "sources": bundle.get("sources", [])}


def _escape_braces(s: str) -> str:
    # make any braces in fetched context literal for later formatting use (defensive)
    return s.replace("{", "{{").replace("}", "}}")


def _draft_plan(topic, beats, words, cfg, tok, mdl, context_block=None):
    # Build the user message WITHOUT str.format over the JSON schema
    if context_block:
        # we still escape in case later someone re-introduces .format somewhere
        safe_ctx = _escape_braces(context_block["context"])
        user = (
            f"Topic: {topic}\n"
            f"Words target: {words}\n"
            f"Beats target: {beats}\n"
            "Use this verified context; prefer its facts and add inline [S#] where appropriate:\n"
            f"{safe_ctx}\n\n"
            "Return ONLY the JSON object in the exact shape below:\n"
            + JSON_SHAPE
        )
    else:
        user = (
            f"Topic: {topic}\n"
            f"Words target: {words}\n"
            f"Beats target: {beats}\n"
            "Return ONLY the JSON object in the exact shape below:\n"
            + JSON_SHAPE
        )

    prompt = tok.apply_chat_template(
        [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
        tokenize=False,
    )

    inputs = tok(prompt, return_tensors="pt").to(mdl.device)
    out = mdl.generate(
        **inputs,
        max_new_tokens=1000,
        temperature=0.2,   # low temp, deterministic JSON
        do_sample=False,   # greedy
        eos_token_id=tok.eos_token_id,
    )
    return tok.decode(out[0], skip_special_tokens=True)


# ---------------------- JSON repair helpers ----------------------

def _find_json_span(s: str) -> str | None:
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return s[start : end + 1]


def _light_repair(s: str) -> str:
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    s = s.replace("```json", "").replace("```", "")
    s = re.sub(r",(\s*[\]\}])", r"\1", s)  # trailing commas
    return s


def _extract_json(text: str) -> dict:
    raw = _find_json_span(text)
    if raw is None:
        raise ValueError("Model did not return JSON text.")
    try:
        return json.loads(raw)
    except Exception:
        fixed = _light_repair(raw)
        return json.loads(fixed)


# ---------------------- Public API ----------------------

def produce_plan(topic, beats, words, cfg):
    tok, mdl = _load()

    ctx_block = _maybe_build_context(topic, cfg)

    txt = _draft_plan(topic, beats, words, cfg, tok, mdl, context_block=ctx_block)

    try:
        plan = _extract_json(txt)
    except Exception:
        reminder = (
            "Return ONLY the JSON object. No extra text. "
            "If you added anything else, remove it and output just the JSON."
        )
        strict_prompt = tok.apply_chat_template(
            [{"role": "system", "content": SYS}, {"role": "user", "content": reminder}],
            tokenize=False,
        )
        out2 = mdl.generate(
            **tok(strict_prompt, return_tensors="pt").to(mdl.device),
            max_new_tokens=200,
            temperature=0.1,
            do_sample=False,
            eos_token_id=tok.eos_token_id,
        )
        txt2 = tok.decode(out2[0], skip_special_tokens=True)
        plan = _extract_json(txt2)

    plan["length_min"] = cfg.length.value
    if ctx_block and ctx_block.get("sources"):
        plan["sources"] = ctx_block["sources"]
    return plan
