import sys, numpy as np
from PIL import Image
C,R=320,180
def decode(path):
    im=np.asarray(Image.open(path).convert('RGB')).astype(int)
    red=(im[:,:,0]>200)&(im[:,:,1]<60)&(im[:,:,2]<60)
    rowc=red.sum(axis=1); colc=red.sum(axis=0)
    rows=np.where(rowc>300)[0]; cols=np.where(colc>200)[0]
    y0,y1,x0,x1=rows.min(),rows.max(),cols.min(),cols.max()
    # canvas outer = C*4+16 by R*4+16 css px
    sx=(x1-x0+1)/(C*4+16); sy=(y1-y0+1)/(R*4+16)
    gray=im.mean(axis=2)
    def bit(r,c):
        cx=x0+(8+c*4+2)*sx; cy=y0+(8+r*4+2)*sy
        return 1 if gray[int(round(cy)),int(round(cx))]<128 else 0
    hdr=[bit(0,i) for i in range(96)]
    vals=[int(''.join(map(str,hdr[i*32:(i+1)*32])),2) for i in range(3)]
    frame,total,n=vals
    out=bytearray()
    for i in range(n):
        b=0
        for k in range(8):
            idx=i*8+k; r=1+idx//C; c=idx%C
            b=(b<<1)|bit(r,c)
        out.append(b)
    return frame,total,bytes(out)
# Uso: python3 decode_frames.py <png do zoom> <pasta de saída>  -> grava frame<N>.bin
f,t,b=decode(sys.argv[1]); import os; os.makedirs(sys.argv[2], exist_ok=True)
open(os.path.join(sys.argv[2], f'frame{f}.bin'),'wb').write(b); print('frame', f, 'total', t, 'bytes', len(b))
