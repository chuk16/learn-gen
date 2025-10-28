import os, subprocess, uuid

OUT = "data/audio"

def synthesize(text: str, model_path: str):
    """
    Uses Piper CLI. You must download a model (.onnx + .json) and pass its ONNX path here.
    Example voices: https://github.com/rhasspy/piper/releases/tag/v0.0.2
    """
    os.makedirs(OUT, exist_ok=True)
    wav_path = os.path.join(OUT, f"narr_{uuid.uuid4().hex}.wav")
    # Piper usage: piper -m <model.onnx> -f <output.wav>
    cmd = ["piper", "-m", model_path, "-f", wav_path]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)
    return wav_path
