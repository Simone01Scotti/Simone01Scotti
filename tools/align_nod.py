"""Allinea la foto 'testa giù' (40) a quella frontale (39) massimizzando la sovrapposizione delle sagome
(spalle e collo restano fermi durante un cenno)."""
import numpy as np, cv2
from PIL import Image
def mask(n, s=0.125):
    a=np.array(Image.open(f'cut_{n}.png'))[:,:,3]
    return cv2.resize(a,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)>128
ref=mask('39'); h,w=ref.shape
src=mask('40')
best=(0,None)
for sc in np.linspace(0.80,1.15,36):
    for dx in range(-30,31,2):
        for dy in range(-40,41,2):
            M=np.float32([[sc,0,dx+(1-sc)*w/2],[0,sc,dy+(1-sc)*h/2]])
            r=cv2.warpAffine(src.astype(np.uint8),M,(w,h))>0
            # peso maggiore alla parte bassa (spalle)
            iou=(r&ref)[int(h*0.55):].sum()/((r|ref)[int(h*0.55):].sum()+1)
            if iou>best[0]: best=(iou,(sc,dx,dy))
print(best)
sc,dx,dy=best[1]; S=8
im=Image.open('cut_40.png'); W,H=im.size
M=np.float32([[sc,0,dx*S+(1-sc)*W/2],[0,sc,dy*S+(1-sc)*H/2]])
out=cv2.warpAffine(np.array(im),M,(W,H))
Image.fromarray(out).save('cut_40a.png')
