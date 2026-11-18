"""Synthesised score for "Born from Code", locked to the 24 fps picture.
Usage: python soundtrack.py out.wav
"""
import sys, wave
import numpy as np

SR, DUR, FPS = 48000, 20.0, 24
n = int(SR * DUR)
t = np.arange(n) / SR
rng = np.random.default_rng(7)
L = np.zeros(n); R = np.zeros(n)

def f2s(frame): return (frame - 1) / FPS
def env_adsr(length, a, d, s, r):
    e = np.ones(length) * s
    ia, idd, ir = int(a * SR), int(d * SR), int(r * SR)
    e[:ia] = np.linspace(0, 1, ia, endpoint=False) if ia else e[:ia]
    e[ia:ia + idd] = np.linspace(1, s, idd, endpoint=False)[: max(0, min(idd, length - ia))]
    if ir: e[-ir:] *= np.linspace(1, 0, ir)
    return e
def add(sig, start, pan=0.0, gain=1.0):
    i = int(start * SR); j = min(n, i + len(sig))
    if j <= i: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.cos((pan + 1) * np.pi / 4)
    R[i:j] += s * np.sin((pan + 1) * np.pi / 4)
def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR); y = np.empty_like(x); acc = 0.0
    for k in range(len(x)):
        acc = (1 - a) * x[k] + a * acc; y[k] = acc
    return y
def smoothstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

# --- Act I-II: warm drone that rises in tension -------------------------------
drone_end = f2s(204)
m = t < drone_end + 0.6
rise = smoothstep((t - f2s(97)) / (drone_end - f2s(97)))
base = 55.0 * (1 + 0.06 * rise)
ph = 2 * np.pi * np.cumsum(base) / SR
drone = (np.sin(ph) + 0.5 * np.sin(1.5 * ph + 0.3) + 0.25 * np.sin(2 * ph) + 0.12 * np.sin(3.01 * ph))
drone *= smoothstep(t / 2.5) * (0.5 + 0.5 * rise) * np.where(t < drone_end, 1, np.clip(1 - (t - drone_end) / 0.5, 0, 1))
add((drone * m)[: n], 0, 0, 0.16)

# data ticks: keystroke-like clicks, sparse then accelerating into the vortex
tick_t = 0.3
while tick_t < drone_end - 0.1:
    k = int(0.012 * SR)
    click = rng.standard_normal(k) * np.exp(-np.linspace(0, 9, k))
    click = np.diff(np.concatenate([[0], click]))          # brighter
    tone = np.sin(2 * np.pi * rng.choice([1760, 2093, 2637, 3136]) * np.arange(k) / SR) * np.exp(-np.linspace(0, 6, k))
    add(click * 0.6 + tone * 0.35, tick_t, rng.uniform(-0.8, 0.8), 0.22)
    prog = tick_t / drone_end
    tick_t += rng.uniform(0.06, 0.32) * (1 - 0.8 * prog)

# riser: filtered noise swell into the ignition
rs, re_ = f2s(120), f2s(203)
k = int((re_ - rs) * SR)
noise = rng.standard_normal(k)
sweep = np.zeros(k); acc = 0.0
cut = 300 + 7000 * np.linspace(0, 1, k) ** 2
a = np.exp(-2 * np.pi * cut / SR)
for i in range(k):
    acc = (1 - a[i]) * noise[i] + a[i] * acc; sweep[i] = acc
sweep *= np.linspace(0, 1, k) ** 2.2
add(sweep, rs, -0.2, 0.22); add(sweep, rs + 0.011, 0.2, 0.22)

# --- Ignition impact (frame ~204) --------------------------------------------
it = f2s(203)
k = int(3.5 * SR); tt = np.arange(k) / SR
sub = np.sin(2 * np.pi * np.cumsum(30 + 50 * np.exp(-tt * 6)) / SR) * np.exp(-tt * 1.3)
burst = lowpass(rng.standard_normal(k), 2500) * np.exp(-tt * 3.5)
add(sub, it, 0, 0.9); add(burst, it, -0.3, 0.5); add(burst * 0.9, it + 0.005, 0.3, 0.5)

# --- Act III-V: shimmering pad (A major add9), then resolve --------------------
def pad(freqs, start, length, gain, attack=1.5, release=2.0):
    k = int(length * SR); tt = np.arange(k) / SR
    sig = np.zeros(k)
    for f in freqs:
        for det in (-0.004, 0.0, 0.004):
            sig += np.sin(2 * np.pi * f * (1 + det) * tt + rng.uniform(0, 6.28)) * (1 + 0.3 * np.sin(2 * np.pi * 0.2 * tt))
    sig /= len(freqs) * 3
    sig *= env_adsr(k, attack, 0.5, 0.85, release)
    add(sig, start, -0.35, gain); add(np.roll(sig, 480), start, 0.35, gain)
pad([220.0, 277.18, 329.63, 493.88], f2s(206), 7.0, 0.28)
pad([110.0, 220.0, 277.18, 329.63, 440.0, 659.25], f2s(372), DUR - f2s(372), 0.30, attack=0.8, release=1.6)

# sparkles during the bloom
for _ in range(26):
    st = rng.uniform(f2s(206), f2s(262))
    f = rng.choice([1760.0, 2217.46, 2637.02, 3322.44])
    k = int(0.5 * SR); tt = np.arange(k) / SR
    add(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9), st, rng.uniform(-1, 1), 0.06)

# --- Morph: voxel "snap" plucks on a pentatonic run, density follows the build --
scale_hz = [440.0, 493.88, 554.37, 659.25, 739.99, 880.0, 987.77, 1108.73, 1318.51]
for i in range(70):
    st = f2s(270) + (i / 70) ** 0.85 * (f2s(350) - f2s(270)) + rng.uniform(-0.02, 0.02)
    f = scale_hz[(i * 3 + rng.integers(0, 2)) % len(scale_hz)]
    k = int(0.35 * SR); tt = np.arange(k) / SR
    pl = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 14)
    add(pl, st, rng.uniform(-0.7, 0.7), 0.09)

# --- Landing thump (frame 366) -------------------------------------------------
lt = f2s(366); k = int(0.9 * SR); tt = np.arange(k) / SR
thump = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-tt * 25)) / SR) * np.exp(-tt * 5) * np.clip(tt / 0.004, 0, 1)
add(thump, lt, 0, 0.75); add(lowpass(rng.standard_normal(k), 900) * np.exp(-tt * 18), lt, 0, 0.3)

# --- Blinks: tiny two-note blips -------------------------------------------------
for fr in (412, 456):
    for j, f in enumerate((1318.51, 1760.0)):
        k = int(0.09 * SR); tt = np.arange(k) / SR
        add(np.sin(2 * np.pi * f * tt) * np.exp(-tt * 40), f2s(fr) + j * 0.07, 0.1, 0.12)

# --- Title chime -------------------------------------------------------------------
for j, f in enumerate((880.0, 1108.73, 1318.51, 1760.0)):
    k = int(3.0 * SR); tt = np.arange(k) / SR
    bell = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 3)) * np.exp(-tt * 1.6)
    add(bell, f2s(430) + j * 0.12, -0.4 + j * 0.27, 0.09)

# --- Reverb (stereo noise-tail convolution) -----------------------------------
def reverb(x, seconds=2.6, seed=1):
    r = np.random.default_rng(seed); k = int(seconds * SR)
    ir = r.standard_normal(k) * np.exp(-np.linspace(0, 7, k)); ir = lowpass(ir, 6000); ir /= np.abs(ir).sum() ** 0.5 * 18
    size = 1 << int(np.ceil(np.log2(len(x) + k)))
    return np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
L = L + 0.55 * reverb(L, seed=1); R = R + 0.55 * reverb(R, seed=2)

# master: fade out, soft clip, normalise
fade = np.clip((DUR - t) / 1.0, 0, 1)
L *= fade; R *= fade
mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.2)
mix /= np.abs(mix).max() / 0.89
out = sys.argv[1] if len(sys.argv) > 1 else "soundtrack.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("WROTE", out)
