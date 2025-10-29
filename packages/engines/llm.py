import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODEL = "Qwen/Qwen2.5-7B-Instruct"
_tok = _mdl = None

def _load():
    global _tok, _mdl
    if _mdl:
        return _tok, _mdl

    _tok = AutoTokenizer.from_pretrained(MODEL, use_fast=True)

    quantization_config = None
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
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
    "You are a planner that outputs only strict JSON for a video explainer pipeline. "
    "Primary medium is procedural animation (ffmpeg overlays + programmatic clips). "
    "Use AI stills only when helpful. Prefer timeline/diagram/path animations. "
    "Avoid photoreal faces. Follow the JSON schema strictly."
)

# Escape literal braces around schema example ({{ }})
TEMPLATE = (
    "Return ONLY a single valid JSON object. No prose, no markdown, no prefix/suffix. "
    "Start the first character with '{{' and end with '}}'.\n"
    "Topic: {topic}\n"
    "Words target: {words}\n"
    "Beats target: {beats}\n"
    "Your JSON keys must include: "
    "topic, length_min, narration_full, "
    "sections (array of objects with keys: id, goal, beats, duration_s). "
    "Each item in sections.beats is an object with keys: type, narration, onscreen, "
    "where onscreen has keys: title, bullets, diagram, anim_path, assets.\n"
    "Example structure (keys only, values are yours): "
    "{{\"topic\":\"...\",\"length_min\":1,\"narration_full\":\"...\","
    "\"sections\":[{{\"id\":\"s1\",\"goal\":\"...\",\"beats\":[{{"
    "\"type\":\"narr\",\"narration\":\"...\",\"onscreen\":{{\"title\":\"...\",\"bullets\":[],"
    "\"diagram\":\"\",\"anim_path\":\"\",\"assets\":[]}}}}],\"duration_s\":6}}]}}"
)

def _balanced_json(text: str):
    start = text.find("{")
    if start == -1:
        return None
    bal = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            bal += 1
        elif ch == "}":
            bal -= 1
            if bal == 0:
                cand = text[start:i+1]
                try:
                    return json.loads(cand)
                except Exception:
                    return None
    return None

def _extract_json(text: str) -> dict:
    # 1) balanced-brace attempt
    obj = _balanced_json(text)
    if obj is not None:
        return obj
    # 2) regex: first {...} that looks like JSON (very permissive)
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise ValueError("Model did not return valid JSON")

def produce_plan(topic, beats, words, cfg):
    tok, mdl = _load()

    prompt = TEMPLATE.format(topic=topic, beats=beats, words=words)

    messages = [
        {"role": "system", "content": SYS},
        {"role": "user", "content": prompt},
    ]
    chat = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = tok(chat, return_tensors="pt").to(mdl.device)

    out = mdl.generate(
        **inputs,
        max_new_tokens=1000,
        temperature=0.2,          # make output deterministic
        do_sample=False,          # force greedy for pure JSON
        pad_token_id=tok.eos_token_id,
        eos_token_id=tok.eos_token_id,
    )

    txt = tok.decode(out[0], skip_special_tokens=True)

    # Try to extract JSON; if it fails once, re-ask with a minimal clarifier
    try:
        plan = _extract_json(txt)
    except Exception:
        repair_messages = [
            {"role": "system", "content": SYS},
            {"role": "user", "content": "Return ONLY a valid JSON object that starts with '{' and ends with '}'. No prose."}
        ]
        repair_chat = tok.apply_chat_template(repair_messages, tokenize=False, add_generation_prompt=True)
        repair_inputs = tok(repair_chat, return_tensors="pt").to(mdl.device)
        repair_out = mdl.generate(
            **repair_inputs,
            max_new_tokens=800,
            temperature=0.2,
            do_sample=False,
            pad_token_id=tok.eos_token_id,
            eos_token_id=tok.eos_token_id,
        )
        repair_txt = tok.decode(repair_out[0], skip_special_tokens=True)
        plan = _extract_json(repair_txt)

    # Inject defaults / required fields
    try:
        length_min = getattr(cfg.length, "value", None)
    except Exception:
        length_min = None
    if length_min is None:
        length_min = max(1, int(round((words or 150) / 150.0)))

    plan.setdefault("topic", topic)
    plan["length_min"] = length_min
    plan.setdefault("narration_full", "")
    plan.setdefault("sections", [])

    return plan
