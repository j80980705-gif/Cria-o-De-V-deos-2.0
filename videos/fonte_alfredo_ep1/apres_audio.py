import os, wave, numpy as np
D = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(D, 'build_audio.py'), encoding='utf-8').read()
helpers = src[src.index('# ---------- synth helpers'):src.index('# moods by line index')]
SR = 44100
TOTAL = 54.0
S = [0, 4.5, 9.5, 14.5, 20, 36, 42, 47.5, 54]
g = {'np': np, 'SR': SR, 'TOTAL': TOTAL}
exec(helpers, g)
exec(src[src.index('def fade('):src.index('ends = [')], g)
render_music, music, sfx, add = g['render_music'], g['music'], g['sfx'], g['add']
render_music('sonho', 0, S[6])
render_music('real', S[6] + 1.4, S[7])
render_music('sonho', S[7], TOTAL)
add(sfx, S[6] + 0.3, g['STING'], .34)
for t in [0.1, S[1] + .2, S[2] + .1, S[3] + .1, S[3] + 1.2, S[5] + .1, S[5] + 1.6, S[7] + .1, S[7] + 2.6]:
    add(sfx, t, g['POP'], .14)
for t in [S[1] + 2.2, S[6] + .35, S[7] + .8]:
    add(sfx, t, g['THUD'], .40)
TS, TD = 21, (S[5] - 21) / 6
for k in range(6):
    add(sfx, TS + k * TD + .45, g['POP'], .16)
end = int(TOTAL * SR)
def out(name, musvol):
    m = (music * musvol + sfx)[:end]
    m[:int(.3 * SR)] *= np.linspace(0, 1, int(.3 * SR))
    m[-int(1.2 * SR):] *= np.linspace(1, 0, int(1.2 * SR))
    m = m / max(1e-6, np.abs(m).max()) * 0.9
    w = wave.open(os.path.join(D, name), 'w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((m * 32767).astype(np.int16).tobytes()); w.close()
out('apres_trilha.wav', 1.0)
print('ok')
