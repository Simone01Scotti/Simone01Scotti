"""Monta i frame ASCII in due SVG animati (tema scuro e chiaro) per il README GitHub."""
import json
from xml.sax.saxutils import escape

d = json.load(open('out/frames.json'))

# Ordine dei frame da sinistra a destra (m = foto specchiata)
LR = ['49m', '46m', '42', '44m', '39', '44', '45', '46', '49']
F = 4  # indice del frame frontale

STEP, HOLD_FRONT, HOLD_SIDE = 0.11, 1.6, 0.5  # secondi
# Timeline: frontale -> destra -> frontale -> sinistra -> frontale
path = [F] + list(range(F + 1, len(LR))) + list(range(len(LR) - 2, -1, -1)) + list(range(1, F))
timeline = []
for i in path:
    dur = HOLD_FRONT if i == F else HOLD_SIDE if i in (0, len(LR) - 1) else STEP
    timeline.append((i, dur))
TOTAL = sum(t for _, t in timeline)

FS, CW, LH = 10, 6.0, 11  # font-size, larghezza carattere, interlinea
COLS = len(d['39']['dark'][0]); ROWS = len(d['39']['dark'])
W, H = COLS * CW, ROWS * LH + 4

def keyframes(idx):
    """Keyframe 'a gradino' che rendono visibile il frame solo nei suoi intervalli."""
    t, on = 0.0, []
    for i, dur in timeline:
        if i == idx:
            on.append((t, t + dur))
        t += dur
    ks = {0.0: 0, 100.0: 0}
    for a, b in on:
        ks[round(b / TOTAL * 100, 3)] = 0
    for a, b in on:  # gli inizi vincono sulle fini coincidenti
        ks[round(a / TOTAL * 100, 3)] = 1
    body = ''.join(f'{p:.3f}%{{opacity:{v}}}' for p, v in sorted(ks.items()))
    return f'@keyframes k{idx}{{{body}}}'

def build(theme):
    fill = '#7ee787' if theme == 'dark' else '#116329'
    css = [
        f'text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono","DejaVu Sans Mono",monospace;'
        f'font-size:{FS}px;fill:{fill};white-space:pre}}',
        f'.f{{opacity:0;animation:{TOTAL:.2f}s step-end infinite}}',
    ]
    for i in range(len(LR)):
        css.append(keyframes(i))
        css.append(f'.f{i}{{animation-name:k{i}}}')
    css.append(f'@media (prefers-reduced-motion:reduce){{.f{{animation:none}}.f{F}{{opacity:1}}}}')

    groups = []
    for i, key in enumerate(LR):
        lines = d[key][theme]
        rows = []
        for r, line in enumerate(lines):
            if not line.strip():
                continue
            # textLength fissa la larghezza riga: allineamento identico con qualsiasi font monospace
            rows.append(f'<text x="0" y="{(r + 1) * LH:.0f}" textLength="{W:.0f}" '
                        f'lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(line)}</text>')
        groups.append(f'<g class="f f{i}">' + ''.join(rows) + '</g>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
            f'role="img" aria-label="Ritratto ASCII animato di Simone">'
            f'<title>Simone in ASCII</title><style>{"".join(css)}</style>' + ''.join(groups) + '</svg>')

for theme in ('dark', 'light'):
    open(f'out/head-{theme}.svg', 'w').write(build(theme))
print(f'{len(LR)} frame, ciclo {TOTAL:.2f}s, {W:.0f}x{H:.0f}px')
