import os, whisper

OUT = "data/captions"
_model = None

def _ts(s: float):
    ms = int((s - int(s)) * 1000); s = int(s)
    h = s // 3600; m = (s % 3600) // 60; s = s % 60
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def to_srt(wav_path: str):
    global _model
    if not _model:
        _model = whisper.load_model("small")  # CPU ok; 'medium' if faster GPU
    res = _model.transcribe(wav_path, word_timestamps=False)
    os.makedirs(OUT, exist_ok=True)
    srt_path = os.path.join(OUT, os.path.basename(wav_path).replace(".wav", ".srt"))
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(res["segments"], start=1):
            f.write(f"{i}\n{_ts(seg['start'])} --> {_ts(seg['end'])}\n{seg['text'].strip()}\n\n")
    return srt_path
