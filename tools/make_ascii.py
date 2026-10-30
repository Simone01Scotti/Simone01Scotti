"""Genera frame ASCII allineati dalle foto scontornate (cut_XX.png)."""
import numpy as np, json, sys
from PIL import Image, ImageOps, ImageFilter
import cv2

# id foto -> (top testa auto, mento y, specchia?)
CHIN = {'39':1720,'42':1700,'44':1695,'45':1690,'46':1690,'49':1720,'41':1680,'40':1890}
COLS, ROWS = 100, 52
RAMP = " .-,_;:!*/|cjfCy3aPmO#QB@"

def load(n, mirror=False):
    im = Image.open(f'cut_{n}.png').convert('RGBA')
    a = np.array(im)[:,:,3] > 128
    rows = np.where(a.sum(1) > 40)[0]; top = rows[0]
    chin = CHIN[n]; H = chin - top
    ny = int(chin + 0.10*H)
    xs = np.where(a[ny])[0]
    cx = (xs[0]+xs[-1])/2
    if mirror:
        im = ImageOps.mirror(im); cx = im.width-1-cx
    return im, top, H, cx

def frame(n, mirror=False, cols=COLS, rows=ROWS, like=None):
    im, top, H, cx = load(like or n, mirror)
    if like: im = Image.open(f'cut_{n}.png').convert('RGBA')
    cw = 1.40*H; y0 = top-0.06*H; ch = 1.32*H
    box = (int(cx-cw/2), int(y0), int(cx+cw/2), int(y0+ch))
    c = im.crop(box)  # area fuori immagine -> trasparente
    rgb = np.array(c)[:,:,:3]; al = np.array(c)[:,:,3].astype(float)/255
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = cv2.addWeighted(g,1.5,cv2.GaussianBlur(g,(0,0),H/60),-0.5,0)
    m = al > 0.5
    lo, hi = np.percentile(g[m], 3), np.percentile(g[m], 99)
    g = np.clip((g-lo)/(hi-lo), 0, 1)*255
    g = cv2.resize(g, (cols, rows), interpolation=cv2.INTER_AREA).astype(float)/255
    al = cv2.resize(al, (cols, rows), interpolation=cv2.INTER_AREA)
    # dissolvenza verso il basso (spalle)
    yy = np.arange(rows)/rows; s0 = 1.10/1.32  # inizio dissolvenza: poco sotto il mento
    fade = (np.clip(1-(yy-s0)/(1-s0), 0, 1)**1.5)[:,None]
    return g, al, fade

def to_ascii(g, al, fade, dark=True):
    # dark theme: pelle chiara -> caratteri densi; light theme: invertito
    v = g if dark else 1-g
    v = v**1.35*(0.15+0.85*fade) if dark else v**0.85*fade**3
    al = al*np.clip(fade*1.6,0,1)
    out=[]
    for r in range(g.shape[0]):
        line=''
        for c in range(g.shape[1]):
            if al[r,c] < 0.45: line+=' '; continue
            k = int(v[r,c]*(len(RAMP)-1)); k=max(k,1)
            line+=RAMP[k]
        out.append(line.rstrip().ljust(g.shape[1]))
    return out

SEQ = [('49',True),('46',True),('42',False),('44',True),('39',False),
       ('44',False),('45',False),('46',False),('49',False)]
if __name__=='__main__':
    data={}
    for n,m in SEQ:
        g,al,fd=frame(n,m)
        key=n+('m' if m else '')
        data[key]={'dark':to_ascii(g,al,fd,True),'light':to_ascii(g,al,fd,False)}
    for n,like in [('40a','39')]:
        g,al,fd=frame(n,like=like); data[n]={'dark':to_ascii(g,al,fd,True),'light':to_ascii(g,al,fd,False)}
    json.dump(data, open('out/frames.json','w'), indent=0)
    print('\n'.join(data['39']['dark']))
