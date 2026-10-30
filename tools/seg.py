from rembg import remove, new_session
from PIL import Image, ImageDraw
import glob, os
s=new_session('u2net_human_seg')
for f in sorted(glob.glob('/mnt/user-data/uploads/*.jpg')):
    n=os.path.basename(f)[-6:-4]
    im=Image.open(f).convert('RGB')
    out=remove(im, session=s, post_process_mask=True)
    out.save(f'cut_{n}.png')
