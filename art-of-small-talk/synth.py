"""Narrate script/*.txt into one mp3 per chapter. Lines starting 'A: ' / 'B: '
are example dialogue, spoken by two other voices."""
import re, subprocess, sys
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).parent
TTS = ROOT.parent / "tts"
OUT = ROOT / "mp3"; OUT.mkdir(exist_ok=True)
NARR, VA, VB = "af_heart", "am_michael", "af_bella"
k = Kokoro(str(TTS / "kokoro.onnx"), str(TTS / "voices.bin"))
SR = 24000
sil = lambda s: np.zeros(int(SR * s), dtype=np.float32)

def sentences(text):
    # keep each synthesis call short: the model truncates very long inputs
    parts, buf = re.split(r"(?<=[.?!])\s+", text.strip()), ""
    for p in parts:
        if len(buf) + len(p) > 350 and buf:
            yield buf; buf = p
        else:
            buf = (buf + " " + p).strip()
    if buf: yield buf

def say(text, voice, speed):
    out = []
    for chunk in sentences(text):
        s, sr = k.create(chunk, voice=voice, speed=speed, lang="en-us")
        assert sr == SR
        out += [s.astype(np.float32), sil(0.22)]
    return np.concatenate(out)

files = sorted((ROOT / "script").glob("*.txt"))
only = sys.argv[1:]
total = 0
for i, f in enumerate(files):
    if only and not any(f.name.startswith(o) for o in only): continue
    paras = [p.strip() for p in f.read_text().split("\n") if p.strip()]
    audio, prev_dialog = [sil(0.6)], False
    for n, p in enumerate(paras):
        m = re.match(r"^([AB]): (.*)", p)
        if m:
            if not prev_dialog: audio.append(sil(0.35))
            audio += [say(m.group(2), VA if m.group(1) == "A" else VB, 1.0), sil(0.3)]
        else:
            if prev_dialog: audio.append(sil(0.5))
            audio += [say(p, NARR, 0.9), sil(1.4 if n == 0 else 0.6)]
        prev_dialog = bool(m)
    audio.append(sil(1.5))
    a = np.concatenate(audio)
    wav = OUT / (f.stem + ".wav"); sf.write(wav, a, SR)
    title = f.stem.split("_", 1)[1].replace("_", " ")
    mp3 = OUT / f"{f.stem}.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
        "-af", "loudnorm=I=-18:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1", "-b:a", "96k",
        "-metadata", f"title={title}", "-metadata", "album=The Art of Small Talk: A Master Class",
        "-metadata", "artist=Claude", "-metadata", "genre=Audiobook",
        "-metadata", f"track={i + 1}/{len(files)}", str(mp3)], check=True)
    wav.unlink()
    total += len(a) / SR
    print(f"{f.stem}: {len(a) / SR / 60:.1f} min", flush=True)
print(f"total {total / 60:.1f} min")
