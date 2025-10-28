import os, subprocess

OUT = "data/final"
os.makedirs(OUT, exist_ok=True)

def _concat_filelist(paths, list_path):
    with open(list_path, "w", encoding="utf-8") as f:
        for p in paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

def compose(clips, wav, srt, fps=30, out_name="final.mp4"):
    """
    1) Concatenate per-beat animation clips.
    2) Mux narration (wav) and hardcode subtitles (srt).
    """
    tmp_concat = os.path.join(OUT, "clips.txt")
    _concat_filelist(clips, tmp_concat)

    composed = os.path.join(OUT, "composed.mp4")
    # concat demuxer requires same codec/size/fps; our anims are all encoded the same way in anim.py
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0","-i", tmp_concat,
        "-c","copy", composed
    ], check=True)

    final_path = os.path.join(OUT, out_name)
    subprocess.run([
        "ffmpeg","-y","-i", composed, "-i", wav,
        "-c:v","libx264","-c:a","aac","-shortest",
        "-vf", "subtitles="+srt.replace("\\","/"),
        final_path
    ], check=True)
    return final_path
