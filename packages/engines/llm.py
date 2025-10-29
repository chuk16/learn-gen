import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL = "Qwen/Qwen2.5-7B-Instruct"
_tok = _mdl = None

def _load():
    """
    Lazy-load tokenizer and model with 4-bit quantization when CUDA is available.
    Falls back to CPU fp32 if needed.
    """
    global _tok, _mdl
    if _mdl:
        return _tok, _mdl

    _tok = AutoTokenizer.from_pretrained(MODEL, use_fast=True)

    quantization_config = None
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    # Prefer 4-bit when GPU is present
    if torch.cuda.is_available():
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )

    _mdl = AutoModelForCausalLM.from_pretrained(
        MODEL,
        device_map="auto",
        torch_dtype=torch_dtype,
        quantization_config=quantization_config,
    )
    return _tok, _mdl


SYS = (
    "Primary medium is procedural animation (ffmpeg overlays + simple programmatic clips). "
    "Use AI stills only when they clarify a concept. Prefer timeline, diagram, and path animations. "
    "Avoid photoreal faces. Follow the JSON schema strictly."
)

# IMPORTANT: escape literal braces in the schema example by doubling them: {{ }}
TEMPLATE = (
    "You are a showrunner creating a fun, factual explainer.\n"
    "Topic: {topic}\nWords target: {words}\nBeats target: {beats}\n"
    "Output JSON with fields: topic, length_min, narration_full, "
    "sections[ id, goal, beats[ type, narration, onscreen {{ title, bullets, diagram, anim_path, assets }}, duration_s ] ]."
)

def _extract_json_block(text: str) -> dict:
    """
    Extract the first JSON object from a text block.
    Tries a quick brace-scan; falls back to naive split.
    """
    # Fast path: find first '{' and scan for matching '}' balance.
    start = text.find("{")
    if start != -1:
        balance = 0
        for i, ch in enumerate(text[start:], start=start):
            if ch == "{":
                balance += 1
            elif ch == "}":
                balance -= 1
                if balance == 0:
                    candidate = text[start:i+1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        break  # fall through to naive path

    # Naive fallback
    try:
        candidate = "{" + text.split("{", 1)[-1]
        return json.loads(candidate)
    except Exception as e:
        raise ValueError(f"Could not parse JSON from model output: {e}\n--- BEGIN OUTPUT ---\n{text}\n--- END OUTPUT ---")


def produce_plan(topic, beats, words, cfg):
    tok, mdl = _load()

    # Build the prompt (only these placeholders are used)
    prompt = TEMPLATE.format(topic=topic, beats=beats, words=words)

    chat = tok.apply_chat_template(
        [{"role": "system", "content": SYS},
         {"role": "user", "content": prompt}],
        tokenize=False
    )

    inputs = tok(chat, return_tensors="pt").to(mdl.device)

    out = mdl.generate(
        **inputs,
