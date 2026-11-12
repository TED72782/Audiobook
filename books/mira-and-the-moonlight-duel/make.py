"""Build the track: narration (Kokoro TTS) mixed with sound effects that are
all synthesized here from sine waves and noise. No recorded samples are used.

Script lines:  N:/M:/G:/V: speech   [sfx:name] one-shot   [bg:name|off] bed under
what follows   [pause:seconds]
Usage: python make.py <dir with kokoro.onnx and voices.bin>
"""
import re, subprocess, sys
from pathlib import Path
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly
from kokoro_onnx import Kokoro

SR = 24000
HERE = Path(__file__).parent
rng = np.random.default_rng(7)
t_ = lambda d: np.arange(int(SR * d)) / SR
sil = lambda d: np.zeros(int(SR * d), dtype=np.float32)

def filt(x, kind, f, order=4):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x)

def env(n, attack=0.01, release=0.05):
    e = np.ones(n); a, r = int(SR * attack), int(SR * release)
    e[:a] = np.linspace(0, 1, a); e[-r:] *= np.linspace(1, 0, r); return e

def saber_tone(freq, phase_jitter=0.0):
    """freq: array of Hz per sample. A buzzy, slightly beating drone."""
    out = 0
    for det, amp in ((1.0, 1.0), (1.012, 0.8)):          # two detuned voices beat against each other
        ph = 2 * np.pi * np.cumsum(freq * det) / SR
        out = out + amp * sum(np.sin(k * ph + k) / k ** 1.1 for k in range(1, 14))
    return filt(out, "low", 2600) / 3.2

def hum(d, f0=92, vol=1.0):
    t = t_(d)
    x = saber_tone(f0 * (1 + 0.006 * np.sin(2 * np.pi * 0.7 * t)))
    return x * (1 + 0.12 * np.sin(2 * np.pi * 6.5 * t)) * vol

def ignite(f0=92, d=0.9):
    t = t_(d); f = f0 * (0.35 + 0.65 * np.minimum(1, t / (d * 0.55)) ** 0.6) + 60 * np.exp(-t * 9)
    x = saber_tone(f) * np.minimum(1, t / 0.12)
    hiss = filt(rng.standard_normal(len(t)), "band", [1800, 6500]) * np.exp(-t * 7) * 0.9
    return (x * 1.2 + hiss) * env(len(t), 0.005, 0.15)

def retract(f0=92, d=0.8):
    t = t_(d); f = f0 * (1 - 0.7 * (t / d) ** 1.5)
    x = saber_tone(f) * (1 - t / d) ** 0.7
    hiss = filt(rng.standard_normal(len(t)), "band", [1500, 5000]) * np.exp(-(d - t) * 9) * 0.5
    return (x * 1.2 + hiss) * env(len(t), 0.02, 0.05)

def swing(f0=92, d=0.55, up=1.75):
    t = t_(d); bump = np.sin(np.pi * t / d) ** 2            # pitch and loudness swell then fall, like a pass-by
    x = saber_tone(f0 * (1 + (up - 1) * bump)) * (0.5 + 1.3 * bump)
    air = filt(rng.standard_normal(len(t)), "band", [500, 2500]) * bump * 0.25
    return (x + air) * env(len(t), 0.03, 0.08)

def clash(d=0.45):
    t = t_(d); n = rng.standard_normal(len(t))
    crack = filt(n, "band", [900, 7000]) * np.exp(-t * 14) * 1.6
    sizzle = filt(n, "high", 3000) * np.exp(-t * 6) * (rng.random(len(t)) > 0.55) * 0.9   # sputtering sparks
    buzz = saber_tone(np.full(len(t), 185.0)) * np.sign(np.sin(2 * np.pi * 47 * t)) * np.exp(-t * 5) * 1.3
    return (crack + sizzle + buzz) * env(len(t), 0.001, 0.1)

def beeps(notes, wobble=0.0):
    """notes: (start Hz, end Hz, seconds) chirps, like a small chatty robot."""
    out = []
    for f1, f2, d in notes:
        t = t_(d); f = np.linspace(f1, f2, len(t)) * (1 + wobble * np.sin(2 * np.pi * 28 * t))
        ph = 2 * np.pi * np.cumsum(f) / SR
        out += [(np.sin(ph) + 0.3 * np.sin(2 * ph)) * env(len(t), 0.008, 0.02) * 0.5, sil(0.035)]
    return np.concatenate(out)

def wind(d, vol=1.0):
    t = t_(d); n = rng.standard_normal(len(t))
    sweep = 500 + 300 * np.sin(2 * np.pi * 0.23 * t) + 150 * np.sin(2 * np.pi * 0.61 * t + 1)
    # whistle: narrow noise band whose centre drifts; approximated by ring-modulating low-passed noise
    low = filt(n, "low", 60) * 14
    whistle = low * np.sin(2 * np.pi * np.cumsum(sweep) / SR)
    rush = filt(n, "band", [150, 900]) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * t))
    return (whistle * 0.5 + rush * 0.5) * vol

def footsteps(n=5, gap=0.62):
    out = []
    for i in range(n):
        t = t_(0.22)
        thud = np.sin(2 * np.pi * (75 - 90 * t) * t) * np.exp(-t * 26) * 1.6
        scuff = filt(rng.standard_normal(len(t)), "band", [300, 1800]) * np.exp(-t * 40) * 0.35
        out += [(thud + scuff) * (0.55 + 0.11 * i), sil(gap - 0.22)]     # getting closer
    return np.concatenate(out)

def clatter():
    out = np.zeros(int(SR * 1.5))
    for start, f in ((0.0, 2300), (0.16, 2900), (0.29, 2500), (0.39, 3100), (0.47, 2700), (0.53, 3000), (0.58, 2800)):
        t = t_(0.12); hit = (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 1.52 * t)) * np.exp(-t * 55)
        hit += filt(rng.standard_normal(len(t)), "high", 2500) * np.exp(-t * 90) * 0.5
        i = int(SR * start); out[i:i + len(hit)] += hit * (0.9 - start)
    t = t_(0.8); slide = filt(rng.standard_normal(len(t)), "band", [1500, 4000]) * np.exp(-t * 4) * 0.12
    i = int(SR * 0.6); out[i:i + len(slide)] += slide
    return out

def bonk():
    t = t_(0.28); f = 520 * np.exp(-t * 9) + 180
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)

def force(d=1.3):
    """A deep rising whoosh for something heavy flying through the air."""
    t = t_(d); n = rng.standard_normal(len(t)); rise = (t / d) ** 2
    rumble = np.sin(2 * np.pi * np.cumsum(45 + 70 * rise) / SR) * (0.4 + rise)
    air = filt(n, "band", [200, 1400]) * rise * 1.2
    return (rumble + air) * env(len(t), 0.2, 0.03)

def crash(d=1.6):
    t = t_(d); n = rng.standard_normal(len(t))
    boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t * 3) + 32) / SR) * np.exp(-t * 4) * 1.8
    crack = filt(n, "band", [300, 3500]) * np.exp(-t * 9) * 1.4
    rubble = filt(n, "band", [500, 4000]) * (rng.random(len(t)) > 0.995).astype(float)   # scattered pebbles
    rubble = np.convolve(rubble, np.exp(-np.arange(400) / 60), "same") * np.exp(-t * 2.2) * 0.5
    return (boom + crack + rubble) * env(len(t), 0.001, 0.4)

def chime(notes, gap=0.2, ring=1.6):
    out = np.zeros(int(SR * (gap * len(notes) + ring)))
    for k, f in enumerate(notes):
        t = t_(ring); bell = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * (2.2 + m)) for m, a in ((1, 1), (2.76, 0.35), (5.4, 0.15)))
        i = int(SR * gap * k); out[i:i + len(bell)] += bell * 0.3
    return out

SFX = {
    "chime": lambda: chime([523, 659, 784, 1047, 880, 1175]),
    "chime_end": lambda: chime([1175, 1047, 784, 880, 659, 784, 1047], gap=0.26, ring=2.6),
    "beep_happy": lambda: beeps([(900, 1500, .09), (1500, 1900, .07), (1300, 2300, .12), (2300, 2000, .06), (1800, 2600, .14)]),
    "beep_worried": lambda: beeps([(1500, 1100, .13), (1150, 800, .16), (950, 620, .24)], wobble=0.03),
    "beep_tune": lambda: beeps([(1047, 1047, .22), (1319, 1319, .22), (1568, 1568, .4)]),
    "beep_proud": lambda: beeps([(1000, 1400, .08), (1400, 1400, .08), (1400, 2100, .1), (2100, 2100, .22)]),
    "beep_giggle": lambda: beeps([(1800, 2200, .06), (1700, 2100, .06), (1900, 2300, .06), (1800, 2200, .06), (2000, 2600, .1)]),
    "bonk": bonk, "force": force, "crash": crash,
    "footsteps": footsteps,
    "ignite": lambda: ignite(92),
    "ignite_low": lambda: ignite(71, 1.0),
    "retract": lambda: retract(92),
    "swing": lambda: swing(92),
    "swing_low": lambda: swing(71, 0.6, 1.6),
    "clash": clash,
    "clash_long": lambda: np.concatenate([clash(0.3)[: int(SR * 0.22)], clash(0.3)[: int(SR * 0.2)], clash(0.7)]),
    "clatter": clatter,
}
SFX_GAIN = {"swing": 0.42, "swing_low": 0.42, "clash": 0.36, "clash_long": 0.36, "ignite": 0.42, "ignite_low": 0.42, "retract": 0.45,
            "footsteps": 0.9, "clatter": 0.6, "crash": 0.55, "force": 0.5, "bonk": 0.6, "chime": 0.9, "chime_end": 0.9}
BEDS = {  # looping background under speech: (maker, gain)
    "hum": (lambda d: hum(d, 92) + 0.8 * hum(d, 71), 0.075),      # both blades lit
    "hum_soft": (lambda d: hum(d, 92), 0.05),
    "wind": (wind, 0.16),
}
VOICES = {"N": ("af_heart", 0.88, 1.0), "M": ("af_sky", 1.0, 1.06), "G": ("bm_george", 0.9, 1.0), "V": ("bm_george", 1.0, 0.84)}

def speak(k, who, text):
    voice, speed, pitch = VOICES[who]
    # pitch != 1: speak at a compensating speed, then resample, which shifts pitch and restores the pace
    s, sr = k.create(text, voice=voice, speed=speed / pitch, lang="en-us")
    s = s.astype(np.float64)
    if pitch != 1:
        s = resample_poly(s, 100, int(round(100 * pitch)))            # play back slower -> deeper (or faster -> higher)
    if who == "V":                                                    # behind a metal mask
        s = filt(s, "band", [140, 2600], 2) * 1.5 + 0.25 * s * np.sin(2 * np.pi * 58 * t_(len(s) / SR)[: len(s)])
    return s

def build(tts_dir):
    k = Kokoro(str(Path(tts_dir) / "kokoro.onnx"), str(Path(tts_dir) / "voices.bin"))
    for f in sorted((HERE / "script").glob("*.txt")):
        main, bed_marks, pos, bed = [], [], 0, None       # bed_marks: (start sample, bed name or None)
        def add(x):
            nonlocal pos
            main.append(np.asarray(x, dtype=np.float64)); pos += len(x)
        add(sil(0.4))
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line: continue
            m = re.match(r"\[(sfx|bg|pause):([\w.]+)\]$", line)
            if m and m[1] == "pause": add(sil(float(m[2])))
            elif m and m[1] == "bg": bed_marks.append((pos, None if m[2] == "off" else m[2]))
            elif m: x = SFX[m[2]](); add(x / max(1e-9, np.abs(x).max()) * SFX_GAIN.get(m[2], 0.7)); add(sil(0.12))
            else:
                who, text = line.split(": ", 1)
                s = speak(k, who, text); add(s / max(1e-9, np.abs(s).max()) * 0.85); add(sil(0.45 if who == "N" else 0.35))
        add(sil(0.8))
        mix = np.concatenate(main)
        bed_marks.append((len(mix), None))
        for (start, name), (end, _) in zip(bed_marks, bed_marks[1:]):
            if not name: continue
            maker, gain = BEDS[name]
            b = maker((end - start) / SR + 0.01)[: end - start]
            b = b / np.abs(b).max() * gain * env(len(b), 0.25, 0.3)
            mix[start:end] += b
        mix = np.clip(mix, -0.98, 0.98).astype(np.float32)
        wav = HERE / "mp3" / (f.stem + ".wav"); sf.write(wav, mix, SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", "loudnorm=I=-17:TP=-1.5:LRA=14",
                        "-ar", "44100", "-ac", "1", "-b:a", "96k", "-metadata", "title=" + f.stem.split("_", 1)[1].replace("_", " "),
                        "-metadata", "album=Mira and the Moonlight Duel", "-metadata", "genre=Audiobook", str(wav.with_suffix(".mp3"))], check=True)
        wav.unlink()
        print(f.stem, f"{len(mix) / SR / 60:.2f} min")

if __name__ == "__main__":
    build(sys.argv[1])
