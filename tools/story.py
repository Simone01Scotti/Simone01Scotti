"""Testa ASCII che segue un bug, lo schiaccia e annuisce a "ship it?".

Tutto è guidato da una timeline campionata: la posizione del bug decide dove guarda la testa,
la testa lo insegue con un po' di ritardo e i frame vicini si dissolvono l'uno nell'altro.
Output: out/head-dark.svg e out/head-light.svg (solo testo + CSS, funzionano nel README GitHub).
"""
import json, math
import numpy as np
from xml.sax.saxutils import escape

P = json.load(open('out/poses.json'))
d = {'39': {'dark': P['yaw'][0]['dark']}}

# Pose di rotazione: (chiave frame, angolo in gradi; negativo = guarda a sinistra di chi osserva)
YAW = [('49m', -90), ('46m', -72), ('42', -48), ('44m', -28), ('39', 0),
       ('44', 28), ('45', 48), ('46', 72), ('49', 90)]
NOD = '40a'
FPS = 30
T = 13.0  # durata del ciclo (s)

FS, CW, LH = 10, 6.0, 11
COLS = len(d['39']['dark'][0]); ROWS = len(d['39']['dark'])
W = COLS * CW                     # 600
HEAD_H = ROWS * LH + 4            # area testa
CAP_Y1, CAP_Y2 = HEAD_H + 22, HEAD_H + 46
H = HEAD_H + 60
CX, CY = W / 2, HEAD_H * 0.40     # centro del volto (circa all'altezza degli occhiali)

# ---------------------------------------------------------------- traiettoria del bug
# (tempo, x, y). Catmull-Rom tra i punti, quindi il volo è curvo e continuo.
WP = [
    (0.0, 700, 120), (1.4, 690, 110),            # fuori scena
    (2.0, 560, 150), (2.5, 515, 230), (2.9, 565, 270), (3.3, 590, 190), (3.7, 535, 160),
    (4.15, 430, 300), (4.55, 300, 345), (4.95, 170, 300),  # passa davanti al mento
    (5.35, 65, 210), (5.75, 30, 150), (6.15, 85, 120), (6.55, 40, 245), (6.95, 95, 190),
    (7.45, 210, 120), (7.85, 300, 150),          # torna al centro, davanti alla fronte
    (8.05, 288, 160), (8.25, 312, 152), (8.45, 300, 158),  # ronza in faccia...
]
SPLAT_T = 8.55                                   # ...e viene schiacciato

def catmull(ts, t):
    pts = WP
    for i in range(len(pts) - 1):
        if pts[i][0] <= t <= pts[i + 1][0]:
            p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
            u = (t - p1[0]) / (p2[0] - p1[0])
            def c(k):
                a, b, cc, dd = p0[k], p1[k], p2[k], p3[k]
                return 0.5 * ((2 * b) + (-a + cc) * u + (2 * a - 5 * b + 4 * cc - dd) * u * u + (-a + 3 * b - 3 * cc + dd) * u ** 3)
            return c(1), c(2)
    return pts[-1][1], pts[-1][2]

def smooth(e0, e1, x):
    x = min(max((x - e0) / (e1 - e0), 0), 1)
    return x * x * (3 - 2 * x)

ts = np.arange(0, T + 1e-9, 1 / FPS)
bug = np.array([catmull(WP, t) for t in ts])
bug_on = np.array([1.0 if 1.4 <= t < SPLAT_T else 0.0 for t in ts])

# ---------------------------------------------------------------- dove guarda la testa
def target_yaw(t, x, on):
    if not on:
        return 0.0
    dx = (x - CX) / (W * 0.42)
    return float(np.clip(np.sign(dx) * min(abs(dx), 1) ** 0.8 * 92, -90, 90))

raw = np.array([target_yaw(t, x, o) for t, (x, y), o in zip(ts, bug, bug_on)])
# inseguimento con molla critica (ritardo naturale, niente scatti), simulato a passo fine
yaw = np.zeros_like(raw); y_, v_ = 0.0, 0.0; omega = 9.0; sub = 8
for i in range(len(ts)):
    for _ in range(sub):
        dt = 1 / FPS / sub
        a = omega * omega * (raw[i] - y_) - 2 * omega * v_
        v_ += a * dt; y_ += v_ * dt
    yaw[i] = y_
yaw[ts >= SPLAT_T + 1.2] *= 0  # sicurezza: dopo lo schiaffo si guarda in camera

# cenno "sì": giù-su-giù-su con easing
def nod(t):
    t0 = 10.35
    def bump(a, b, peak):
        if t < a or t > b: return 0
        return peak * math.sin(math.pi * (t - a) / (b - a)) ** 2
    return bump(t0, t0 + 0.55, 1.0) + bump(t0 + 0.55, t0 + 1.0, 0.75)
pitch = np.array([nod(t) for t in ts])

# ---------------------------------------------------------------- scelta della posa
# Pose dense (foto reali + intermedi da optical flow): a ogni campione si mostra la più vicina.
POSES = [('y', i, p) for i, p in enumerate(P['yaw'])] + [('n', i, p) for i, p in enumerate(P['nod']) if i > 0]
YAWS = np.array([p['a'] for p in P['yaw']])
FRONT = int(np.argmin(np.abs(YAWS)))
def pose_at(y, p):
    if p > 0.02:
        k = int(round(p * (len(P['nod']) - 1)))
        return len(P['yaw']) + k - 1 if k > 0 else FRONT
    return int(np.argmin(np.abs(YAWS - y)))
CUR = [pose_at(y, p) for y, p in zip(yaw, pitch)]

# ---------------------------------------------------------------- didascalie e splat
def ramp(t, a, b, fade=0.25):
    return smooth(a, a + fade, t) * (1 - smooth(b - fade, b, t))

CAP1 = 'bug fixed ✓'
CAP2 = 'ship it? [y/n] '
TYPE_T0, TYPE_DT = 9.3, 0.07
YES_T = 11.55
END_T = 12.75

def splat(t):  return ramp(t, SPLAT_T, SPLAT_T + 0.7, 0.06)
def cap1(t):   return ramp(t, SPLAT_T + 0.25, END_T)
def prefix_op(n, t):  # n = numero di caratteri del prefisso di CAP2
    a = TYPE_T0 + (n - 1) * TYPE_DT
    b = TYPE_T0 + n * TYPE_DT if n < len(CAP2) else END_T
    return 1.0 if a <= t < b else 0.0
def yes(t):     return 1.0 if YES_T <= t < END_T else 0.0
def cursor(t):  # cursore lampeggiante mentre aspetta la risposta
    if not (TYPE_T0 + len(CAP2) * TYPE_DT <= t < YES_T): return 0.0
    return 1.0 if int((t - TYPE_T0) * 3) % 2 == 0 else 0.0

# ---------------------------------------------------------------- CSS keyframes
def kf(name, vals, prop=lambda v: f'opacity:{v:g}'):
    """Tiene solo i campioni in cui la curva cambia, poi interpola linearmente."""
    vals = list(vals); n = len(vals); keep = []
    for i, v in enumerate(vals):
        if i in (0, n - 1) or vals[i - 1] != v or vals[i + 1] != v:
            keep.append(i)
    body = ''.join(f'{ts[i] / T * 100:.2f}%{{{prop(vals[i])}}}' for i in keep)
    return f'@keyframes {name}{{{body}}}'

def r2(x): return round(float(x), 2)

def build(theme):
    fg = '#7ee787' if theme == 'dark' else '#116329'
    bg = '#0d1117' if theme == 'dark' else '#ffffff'
    accent = '#f0883e' if theme == 'dark' else '#bc4c00'
    muted = '#8b949e' if theme == 'dark' else '#59636e'
    css = [
        'text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono","DejaVu Sans Mono",monospace;white-space:pre}',
        f'.h text{{font-size:{FS}px;fill:{fg}}}',
        f'.a{{opacity:0;animation:{T}s linear infinite}}',
        f'.cap{{font-size:15px;fill:{fg}}}.mut{{fill:{muted}}}.acc{{fill:{accent};font-weight:700}}',
        '.wing{animation:flap .16s steps(1) infinite}.wing2{animation:flap .16s steps(1) infinite reverse}',
        '@keyframes flap{0%{opacity:1}50%{opacity:0}}',
    ]
    els = []

    # testa: un gruppo per posa, visibile solo quando è la posa corrente
    for i, (_, _, p) in enumerate(POSES):
        vals = [1.0 if c == i else 0.0 for c in CUR]
        if not any(vals):
            continue
        css.append(kf(f'h{i}', vals)); css.append(f'.h{i}{{animation-name:h{i}}}')
        rows = ''.join(
            f'<text x="0" y="{(r + 1) * LH}" textLength="{W:.0f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(l)}</text>'
            for r, l in enumerate(p[theme]) if l.strip())
        els.append(f'<g class="h a h{i}">{rows}</g>')

    # bug: posizione + visibilità; dietro un piccolo tondo col colore di sfondo per staccarlo dall'ASCII
    pos = [f'transform:translate({x:.1f}px,{y:.1f}px)' for x, y in bug]
    body = ''.join(f'{t / T * 100:.2f}%{{{p}}}' for t, p in zip(ts, pos))
    css.append(f'@keyframes bm{{{body}}}')
    css.append(kf('bo', [float(v) for v in bug_on]))
    css.append(f'.bug{{animation:bm {T}s linear infinite}}.bugo{{opacity:0;animation:bo {T}s linear infinite}}')
    els.append(
        f'<g class="bug"><g class="bugo">'
        f'<circle r="18" fill="{bg}" opacity=".85"/>'
        f'<text class="acc wing" x="0" y="7" text-anchor="middle" font-size="22">\\o/</text>'
        f'<text class="acc wing2" x="0" y="7" text-anchor="middle" font-size="22">-o-</text>'
        f'</g></g>')

    # splat nel punto dello schiaffo
    sx, sy = catmull(WP, SPLAT_T - 0.01)
    css.append(kf('sp', [r2(splat(t)) for t in ts])); css.append('.sp{animation-name:sp}')
    els.append(f'<g class="a sp"><circle cx="{sx:.0f}" cy="{sy:.0f}" r="15" fill="{bg}" opacity=".85"/>'
               f'<text class="acc" x="{sx:.0f}" y="{sy + 7:.0f}" text-anchor="middle" font-size="22">*</text></g>')

    # didascalie (larghezza carattere ~0.6em: le righe partono allineate a sinistra, centrate sul totale)
    cw = 15 * 0.6
    css.append(kf('c1', [r2(cap1(t)) for t in ts])); css.append('.c1{animation-name:c1}')
    els.append(f'<text class="cap a c1" x="{W / 2:.0f}" y="{CAP_Y1}" text-anchor="middle">'
               f'<tspan class="mut">// </tspan>{escape(CAP1)}</text>')
    x2 = W / 2 - (len(CAP2) + 1) * cw / 2
    for n in range(1, len(CAP2) + 1):
        css.append(kf(f'p{n}', [prefix_op(n, t) for t in ts])); css.append(f'.p{n}{{animation-name:p{n}}}')
        els.append(f'<text class="cap a p{n}" x="{x2:.1f}" y="{CAP_Y2}" xml:space="preserve">'
                   f'<tspan class="mut">$ </tspan>{escape(CAP2[:n])}</text>')
    xc = x2 + (2 + len(CAP2)) * cw
    css.append(kf('cu', [cursor(t) for t in ts])); css.append('.cu{animation-name:cu}')
    els.append(f'<text class="cap a cu" x="{xc:.1f}" y="{CAP_Y2}">▌</text>')
    css.append(kf('ys', [yes(t) for t in ts])); css.append('.ys{animation-name:ys}')
    els.append(f'<text class="cap a ys acc" x="{xc:.1f}" y="{CAP_Y2}">y \U0001F680</text>')

    css.append('@media (prefers-reduced-motion:reduce){.a,.bug,.bugo{animation:none}'+f'.h{FRONT}{{opacity:1}}'+'}')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
            f'role="img" aria-label="Ritratto ASCII animato di Simone che insegue un bug, lo schiaccia e annuisce a ship it">'
            f'<title>Simone vs bug</title><style>{"".join(css)}</style>{"".join(els)}</svg>')

for theme in ('dark', 'light'):
    open(f'out/head-{theme}.svg', 'w').write(build(theme))
print(f'ciclo {T}s, {W:.0f}x{H:.0f}px, yaw max {yaw.max():.0f} min {yaw.min():.0f}')
