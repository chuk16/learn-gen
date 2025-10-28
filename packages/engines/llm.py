import json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "Qwen/Qwen2.5-7B-Instruct"
_tok = _mdl = None

def _load():
    global _tok, _mdl
    if _mdl: return _tok, _mdl
    _tok = AutoTokenizer.from_pretrained(MODEL, use_fast=True)
    _mdl = AutoModelForCausalLM.from_pretrained(
        MODEL,
        device_map="auto",
        load_in_4bit=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
    )
    return _tok, _mdl

SYS = (
  "Primary medium is procedural animation (ffmpeg overlays + simple programmatic clips). "
  "Use AI stills only when they clarify a concept. Prefer timeline, diagram, and path animations. "
  "Avoid photoreal faces. Follow the JSON schema strictly."
)

TEMPLATE = (
    "You are a showrunner creating a fun, factual explainer.\n"
    "Topic: {topic}\nWords target: {words}\nBeats target: {beats}\n"
    "Output JSON with fields: topic, length_min, narration_full, "
    "sections[id,goal,beats[type,narration,onscreen{title,bullets,diagram,anim_path,assets},duration_s]]."
)

def produce_plan(topic, beats, words, cfg):
    tok, mdl = _load()
    prompt = TEMPLATE.format(topic=topic, beats=beats, words=words)
    chat = tok.apply_chat_template(
        [{"role":"system","content": SYS}, {"role":"user","content": prompt}],
        tokenize=False
    )
    out = mdl.generate(**tok(chat, return_tensors="pt").to(mdl.device),
                       max_new_tokens=1400, temperature=0.7)
    txt = tok.decode(out[0], skip_special_tokens=True)
    # naive JSON recovery; replace with a safer parser in production
    json_str = txt.split("{", 1)[-1]
    json_str = "{" + json_str
    plan = json.loads(json_str)
    plan["length_min"] = cfg.length.value
    return plan
