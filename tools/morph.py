"""Pose dense: crea frame intermedi tra foto vicine (optical flow) e li converte in ASCII."""
import json, numpy as np, cv2
from PIL import Image
import make_ascii as M

WW = 500  # larghezza di lavoro della crop
def crop(n, mirror=False, like=None):
    im, top, H, cx = M.load(like or n, mirror)
    if like: im = Image.open(f'cut_{n}.png').convert('RGBA')
    cw = 1.40*H; y0 = top-0.06*H; ch = 1.32*H
    c = im.crop((int(cx-cw/2), int(y0), int(cx+cw/2), int(y0+ch)))
    hh = round(WW*1.32/1.40)
    a = np.array(c.resize((WW, hh), Image.LANCZOS)).astype(np.float32)/255
    return a  # RGBA float

def flow(a, b):
    ga = cv2.cvtColor((a[:,:,:3]*a[:,:,3:]*255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor((b[:,:,:3]*b[:,:,3:]*255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
    dis.setFinestScale(1); dis.setPatchSize(12); dis.setGradientDescentIterations(25)
    dis.setVariationalRefinementIterations(10)
    return dis.calc(ga, gb, None)

def warp(img, fl, s):
    h, w = fl.shape[:2]
    gx, gy = np.meshgrid(np.arange(w), np.arange(h))
    mx = (gx + fl[:,:,0]*s).astype(np.float32); my = (gy + fl[:,:,1]*s).astype(np.float32)
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

def inbetween(a, b, fab, fba, u):
    # backward warping: pixel del frame intermedio presi da A (spostati di -u*flow) e da B
    wa = warp(a, fba, u)        # usa flow B->A scalato
    wb = warp(b, fab, 1-u)
    return (1-u)*wa + u*wb

def to_ascii(rgba):
    rgb = (np.clip(rgba[:,:,:3],0,1)*255).astype(np.uint8); al = rgba[:,:,3]
    H = WW/1.40
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = cv2.addWeighted(g,1.5,cv2.GaussianBlur(g,(0,0),H/60),-0.5,0)
    m = al > 0.5
    lo, hi = np.percentile(g[m],3), np.percentile(g[m],99)
    g = np.clip((g-lo)/(hi-lo),0,1)
    g = np.clip(cv2.resize(g,(M.COLS,M.ROWS),interpolation=cv2.INTER_AREA),0,1)
    al = cv2.resize(al,(M.COLS,M.ROWS),interpolation=cv2.INTER_AREA)
    yy = np.arange(M.ROWS)/M.ROWS; s0 = 1.10/1.32
    fade = (np.clip(1-(yy-s0)/(1-s0),0,1)**1.5)[:,None]
    return {'dark': M.to_ascii(g, al, fade, True), 'light': M.to_ascii(g, al, fade, False)}

def chain(keys_angles, n_between):
    """keys_angles: lista di ((id, mirror, like), angolo). Restituisce [(angolo, rgba)]."""
    imgs = [crop(*k) for k, _ in keys_angles]
    out = [(keys_angles[0][1], imgs[0])]
    for i in range(len(imgs)-1):
        a, b = imgs[i], imgs[i+1]; A0, A1 = keys_angles[i][1], keys_angles[i+1][1]
        fab, fba = flow(a, b), flow(b, a)
        for j in range(1, n_between+1):
            u = j/(n_between+1)
            out.append((A0+(A1-A0)*u, inbetween(a, b, fab, fba, u)))
        out.append((A1, b))
    return out

if __name__ == '__main__':
    yaw_keys = [(('49',True,None),-90),(('46',True,None),-72),(('42',False,None),-48),(('44',True,None),-28),
                (('39',False,None),0),(('44',False,None),28),(('45',False,None),48),(('46',False,None),72),(('49',False,None),90)]
    yaw = chain(yaw_keys, 3)
    nod = chain([(('39',False,None),0),(('40a',False,'39'),1)], 5)
    data = {'yaw': [{'a': round(a,2), **to_ascii(im)} for a, im in yaw],
            'nod': [{'a': round(a,3), **to_ascii(im)} for a, im in nod]}
    json.dump(data, open('out/poses.json','w'))
    # anteprima di una transizione
    strip = np.concatenate([np.clip(im,0,1)[:,:,:3] for a, im in yaw[16:25]], axis=1)
    Image.fromarray((strip*255).astype(np.uint8)).resize((strip.shape[1]//2, strip.shape[0]//2)).save('morph_strip.png')
    print(len(data['yaw']), 'pose yaw,', len(data['nod']), 'pose cenno')
