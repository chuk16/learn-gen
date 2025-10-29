import os, subprocess, tempfile

OUT = "data/final"
os.makedirs(OUT, exist_ok=True)


def _concat_filelist(paths, list_path):
    with open(list_path, "w", encoding="utf-8") as f:
        for p in paths:
            f.write(f"file '{os.path.abspath(p)}'\n")


def _synthesize_blank_video(duration_s: float, fps: int, out_path: str, width=1920, height=1080):
    # Solid dark background for the given duration
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d={max(1.0, duration_s)}",
        "-vf", f"fps={fps},format=yuv420p",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        out_path
    ], check=True)
    return out_path


def compose(clips, wav, srt, fps=30, out_name="final.mp4"):
    """
    1) Concatenate per-beat animation clips (or synthesize a blank if empty).
    2) Mux narration (wav) and burn subtitles (srt).
    """
    os.makedirs(OUT, exist_ok=True)

    composed = os.path.join(OUT, "composed.mp4")

    if clips:
        tmp_list = os.path.join(OUT, "clips.txt")
        _concat_filelist(clips, tmp_list)
        # concat demuxer: inputs must match codec/size/fps (our anims do)
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", tmp_list,
            "-c", "copy", composed
        ], check=True)
    else:
        # As a last resort (shouldn't happen after orchestrator fix), create a 10s blank
        _synthesize_blank_video(10.0, fps, composed)

    final_path = os.path.join(OUT, out_name)
    # Burn subtitles and add audio; if srt is missing, drop the filter
    vf = []
    if srt and os.path.isfile(srt):
        vf = ["-vf", "subtitles=" + srt.replace("\\", "/")]

    cmd = [
        "ffmpeg", "-y",
        "-i", composed, "-i", wav,
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        *vf,
        final_path
    ]
    subprocess.run(cmd, check=True)
    return final_path
