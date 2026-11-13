import json, wave, re, sys, os
import numpy as np

SR = 44100
D = os.path.dirname(os.path.abspath(__file__))

def read_wav(p):
    w = wave.open(p)
    sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    if w.getnchannels() == 2:
        a = a.reshape(-1, 2).mean(1)
    if sr != SR:
        x = np.arange(0, len(a), sr / SR)
        a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
    return a

lines = [l.strip() for l in open(os.path.join(D, 'lines.txt'), encoding='utf-8') if l.strip()]
gaps = [0.35, 0.35, 0.55, 1.0, 1.0, 2.1, 0.55, 0.6, 0.4, 0.5, 1.4]
voice = [read_wav(os.path.join(D, f'l{i+1}.wav')) for i in range(len(lines))]

t = 0.35
starts = []
for v, g in zip(voice, gaps):
    starts.append(t)
    t += len(v) / SR + g
TOTAL = round(t, 2)

# ---------- timeline (words with estimated timings) ----------
RED = {'descolou', 'desafinou', 'esvaziou', 'zero', 'cebola'}
YEL = {'alfredo', 'catorze', 'nova', 'interior', 'tânia', 'perfeito', 'tênis', 'fundo', 'popular', 'primeira', 'chamada',
       'recreio', 'ovo', 'cem', 'expectativa', 'amigos', 'dupla', 'você', 'a:', 'b:', 'comenta', 'dois!', 'riu', 'quieta', 'escada'}
tl = {'total': TOTAL, 'lines': []}
for i, (txt, v, s) in enumerate(zip(lines, voice, starts)):
    dur = len(v) / SR
    words = txt.replace('...', '…').split()
    w8 = [len(re.sub(r'[^\wÀ-ú]', '', w)) + 1.5 + (2.5 if re.search(r'[.,:!…]$', w) else 0) for w in words]
    tot = sum(w8)
    cur = s + 0.06
    span = dur - 0.15
    ws = []
    for w, k in zip(words, w8):
        d = span * k / tot
        key = re.sub(r'[.,…]', '', w.lower())
        col = 'r' if key.strip('!:') in RED else ('y' if key in YEL or key.strip('!:') in YEL else '')
        ws.append({'w': w, 's': round(cur, 3), 'e': round(cur + d, 3), 'c': col})
        cur += d
    # caption chunks: 2-3 words, break after punctuation
    chunks, curc = [], []
    for wd in ws:
        curc.append(wd)
        if len(curc) == 3 or (re.search(r'[.,:!…]$', wd['w']) and (len(curc) >= 2 or len(wd['w']) >= 7)):
            chunks.append(curc); curc = []
    if curc:
        chunks.append(curc)
    tl['lines'].append({'text': txt, 's': round(s, 3), 'e': round(s + dur, 3), 'chunks': chunks})
json.dump(tl, open(os.path.join(D, 'timeline.json'), 'w'), ensure_ascii=False)

# ---------- synth helpers ----------
N = int(TOTAL * SR) + SR
music = np.zeros(N, np.float32)
sfx = np.zeros(N, np.float32)
vo = np.zeros(N, np.float32)

def hz(m): return 440 * 2 ** ((m - 69) / 12)

def env(n, att=0.01, rel=None):
    e = np.ones(n, np.float32)
    a = max(1, int(att * SR))
    e[:a] = np.linspace(0, 1, a)
    e *= np.exp(-np.linspace(0, 5, n)) if rel is None else 1
    return e

def osc(kind, f, dur):
    n = int(dur * SR); tt = np.arange(n) / SR
    ph = (f * tt) % 1
    if kind == 'sine': return np.sin(2 * np.pi * f * tt)
    if kind == 'square': return np.where(ph < .5, 1., -1.)
    if kind == 'saw': return 2 * ph - 1
    return 4 * np.abs(ph - .5) - 1  # triangle

def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); acc = 0.0
    # vectorised one-pole via lfilter-like loop on small arrays is ok
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y

def add(buf, t0, sig, vol):
    i = int(t0 * SR)
    if i >= len(buf): return
    sig = sig[:len(buf) - i]
    buf[i:i + len(sig)] += sig.astype(np.float32) * vol

cache = {}
def tone(kind, m, dur, cutoff=None):
    k = (kind, m, round(dur, 3), cutoff)
    if k not in cache:
        s = osc(kind, hz(m), dur) * env(int(dur * SR))
        if cutoff: s = lowpass(s, cutoff)
        cache[k] = s.astype(np.float32)
    return cache[k]

rng = np.random.default_rng(1)
def noise(dur, hp=True):
    n = int(dur * SR); x = rng.uniform(-1, 1, n).astype(np.float32)
    if hp: x = x - lowpass(x, 3000)
    return x * np.exp(-np.linspace(0, 6, n))
HAT = noise(0.05); SNARE = noise(0.14, hp=False) * 0.6

def kick():
    n = int(0.2 * SR); tt = np.arange(n) / SR
    f = 140 * np.exp(-tt * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 22)
KICK = kick()

SONGS = {
    'sonho': dict(bpm=116, roots=[48, 43, 45, 41], chords=[[60, 64, 67], [59, 62, 67], [60, 64, 69], [60, 65, 69]],
                  mel=[72,0,76,0,79,0,76,0,77,76,74,0,72,0,0,0, 74,0,79,0,83,0,79,0,81,79,77,0,74,0,0,0,
                       76,0,72,0,69,0,72,0,76,77,79,0,76,0,0,0, 77,0,76,0,74,0,72,0,74,0,0,0,67,0,71,0]),
    'real': dict(bpm=88, roots=[45, 50, 40, 45], fifths=[52, 57, 47, 52],
                 mel=[69,0,0,72,0,0,71,0,69,0,0,0,64,0,0,0, 65,0,0,69,0,0,67,0,65,0,0,0,62,0,0,0,
                      64,0,68,0,71,0,74,0,72,0,71,0,68,0,0,0, 69,0,0,0,64,0,0,0,57,0,0,0,0,0,0,0]),
}

def render_music(mood, t0, t1):
    s = SONGS[mood]; sp = 60 / s['bpm'] / 4
    t = t0; step = 0
    while t < t1:
        bar = (step // 16) % 4; b = step % 16
        if mood == 'sonho':
            if b in (0, 8): add(music, t, KICK, .45)
            if b % 2 == 0: add(music, t, HAT, .05)
            if b in (4, 12): add(music, t, SNARE, .12)
            if b in (0, 6, 8, 14): add(music, t, tone('tri', s['roots'][bar], sp * 1.6), .30)
            if b == 10: add(music, t, tone('tri', s['roots'][bar] + 7, sp * 1.6), .26)
            if b in (4, 12):
                for m in s['chords'][bar]: add(music, t, tone('square', m, sp * 1.4, 2200), .035)
            m = s['mel'][step % 64]
            if m: add(music, t, tone('square', m, sp * 1.8, 3200), .055)
        else:
            if b % 4 == 0: add(music, t, tone('saw', s['roots'][bar] if b % 8 == 0 else s['fifths'][bar], sp * 1.3, 520), .25)
            if b in (2, 6, 10, 14): add(music, t, tone('sine', 84 if b % 8 == 2 else 79, 0.06), .18)
            m = s['mel'][step % 64]
            if m: add(music, t, tone('tri', m, sp * 2.4, 2400), .15)
        t += sp; step += 1

# moods by line index: 0-2 sonho, 3-7 real, 8-10 sonho
seg_sonho1 = (0, starts[3] - 0.05)
seg_real = (starts[3] - 0.05, starts[8] - 0.2)
seg_sonho2 = (starts[8] - 0.2, TOTAL)
render_music('sonho', *seg_sonho1)
render_music('real', *seg_real)
render_music('sonho', *seg_sonho2)

def fade(buf, a, b, up):
    i, j = int(a * SR), int(b * SR)
    buf[i:j] *= np.linspace(0, 1, j - i) if up else np.linspace(1, 0, j - i)

# sting "deu ruim"
def sting(short=False):
    notes = [58, 57, 56, 55] if not short else [62, 58]
    lens = [0.38, 0.38, 0.38, 1.3] if not short else [0.18, 0.5]
    out = []
    for i, (m, L) in enumerate(zip(notes, lens)):
        n = int(L * SR); tt = np.arange(n) / SR
        vib = 1 + (0.012 * np.sin(2 * np.pi * 6 * tt) if i == len(notes) - 1 else 0)
        ph = np.cumsum(hz(m) * vib) / SR
        x = (2 * (ph % 1) - 1)
        x = lowpass(x, 1100)
        e = np.ones(n); a = int(.03 * SR); e[:a] = np.linspace(0, 1, a); r = int(.08 * SR); e[-r:] = np.linspace(1, 0, r)
        out.append(x * e)
    return np.concatenate(out).astype(np.float32)

STING = sting(); BLIP = sting(True)
def pop():
    n = int(0.12 * SR); tt = np.arange(n) / SR
    f = 500 + 1400 * tt / 0.12
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 30)).astype(np.float32)
POP = pop()
def thud():
    n = int(0.25 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * np.cumsum(90 * np.exp(-tt * 8) + 40) / SR) * np.exp(-tt * 14) + noise(0.25, False) * 0.25).astype(np.float32)
THUD = thud()

ends = [s + len(v) / SR for s, v in zip(starts, voice)]
add(sfx, ends[3] + 0.05, BLIP, .30)
add(sfx, ends[4] + 0.05, BLIP, .30)
add(sfx, ends[5] + 0.1, STING, .32)
for k in range(len(lines)):
    add(sfx, starts[k] - 0.05, POP, .12)
zw=[w for w in tl['lines'][7]['chunks'][-1] if w['w'].lower().startswith('zero')][0]
add(sfx, zw['s'], THUD, .45)   # zero stamp
add(sfx, starts[0] + 1.6, THUD, .35)   # aluno novo stamp

for s, v in zip(starts, voice):
    add(vo, s, v, 1.0)

# duck music under voice
duck = np.ones(N, np.float32) * 1.0
for s, v in zip(starts, voice):
    i, j = int((s - .1) * SR), int((s + len(v) / SR + .1) * SR)
    duck[max(0, i):j] = 0.38
k = int(0.08 * SR)
duck = np.convolve(duck, np.ones(k) / k, mode='same')
mix = music * duck * 0.9 + sfx + vo * 1.15
# fade music tail
end = int(TOTAL * SR)
mix = mix[:end]
mix[-int(.8 * SR):] *= np.linspace(1, 0, int(.8 * SR))
mix = mix / max(1e-6, np.abs(mix).max()) * 0.92
pcm = (mix * 32767).astype(np.int16)
w = wave.open(os.path.join(D, 'mix.wav'), 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()

# also music-only track for the user
mo = music[:end] * 0.9 + sfx[:end]
mo = mo / max(1e-6, np.abs(mo).max()) * 0.9
w = wave.open(os.path.join(D, 'trilha.wav'), 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mo * 32767).astype(np.int16).tobytes()); w.close()
print('total', TOTAL, 'starts', [round(x, 2) for x in starts])

# version without narration (music ducked where the narrator speaks + sfx)
nv = (music * duck * 0.9 + sfx)[:end]
nv[-int(.8 * SR):] *= np.linspace(1, 0, int(.8 * SR))
nv = nv / max(1e-6, np.abs(nv).max()) * 0.9
w = wave.open(os.path.join(D, 'sem_voz.wav'), 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((nv * 32767).astype(np.int16).tobytes()); w.close()
