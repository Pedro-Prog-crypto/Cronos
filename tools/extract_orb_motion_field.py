"""Extract the clean moving light field from a user-supplied MP4.

Requires ffmpeg, numpy, scipy and Pillow. The original video is never bundled.
"""
from pathlib import Path
import argparse
import subprocess
import numpy as np
from scipy.ndimage import gaussian_filter,map_coordinates,grey_closing
from PIL import Image
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('video',type=Path,help='Source MP4, kept outside the release')
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'frontend/src/assets/images/orb-motion-field.png')
args=parser.parse_args()
source=str(args.video)
width,height=576,1024
count=105
process=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-i',source,'-t','3.5','-vf','fps=30','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
angles=(np.arange(256)+.5)*2*np.pi/256-np.pi
radii=35+(np.arange(64)+.5)*60/64
x=300+np.cos(angles)[:,None]*radii[None,:]
y=489-np.sin(angles)[:,None]*radii[None,:]
coords=np.array([y.ravel(),x.ravel()])
field=[]
for index in range(count):
 data=process.stdout.read(width*height*3)
 if len(data)!=width*height*3:break
 im=np.frombuffer(data,dtype=np.uint8).reshape(height,width,3)
 g=im[375:606,185:416,1].astype(np.float32)
 b=im[375:606,185:416,2].astype(np.float32)
 luminance=g+.13*b
 residual=np.maximum(0,luminance-gaussian_filter(luminance,6)-2.2)
 cx=np.array([y.ravel()-375,x.ravel()-185])
 sampled=map_coordinates(residual,cx,order=1,mode='nearest').reshape(256,64)
 # Source videos contain compression grain; retain bright contours and moving glints.
 sampled=np.clip((sampled-1.2)/32,0,1)**.75
 field.append(np.uint8(sampled*255))
process.stdout.close();process.wait()
if len(field)!=count: raise RuntimeError(f'Expected {count} source frames, got {len(field)}')
raw=np.asarray(field,dtype=np.float32)
repaired=grey_closing(raw,size=(3,9,3),mode='nearest')
smooth=gaussian_filter(raw*.48+repaired*.52,sigma=(.7,1.15,.7),mode=('nearest','wrap','nearest'))
for offset in range(8):
 blend=(8-offset)/9
 edge=(smooth[:,offset,:]+smooth[:,-1-offset,:])*.5
 smooth[:,offset,:]=smooth[:,offset,:]*(1-blend)+edge*blend
 smooth[:,-1-offset,:]=smooth[:,-1-offset,:]*(1-blend)+edge*blend
field=np.uint8(np.clip(smooth*1.04,0,255))
weights=np.maximum(field.astype(np.float32)-70,0)**1.5
total=weights.sum(axis=2)
positions=np.arange(64,dtype=np.float32)
center=(weights*positions).sum(axis=2)/np.maximum(1,total)
spread=np.sqrt((weights*(positions[None,None,:]-center[:,:,None])**2).sum(axis=2)/np.maximum(1,total))
center=gaussian_filter(center,sigma=(1.1,3.0),mode=('nearest','wrap'))
spread=gaussian_filter(spread,sigma=(1.1,3.0),mode=('nearest','wrap'))
inner=np.clip(center-np.maximum(2.4,spread*.58),1,62)/63
outer=np.clip(center+np.maximum(2.4,spread*.58),1,62)/63
cols=8;rows=(len(field)+cols-1)//cols
atlas=np.zeros((rows*64,cols*256,3),dtype=np.uint8)
for i,a in enumerate(field):
 tile=atlas[(i//cols)*64:(i//cols+1)*64,(i%cols)*256:(i%cols+1)*256]
 tile[:,:,0]=a.T
 tile[:,:,1]=np.uint8(inner[i,None,:].repeat(64,axis=0)*255)
 tile[:,:,2]=np.uint8(outer[i,None,:].repeat(64,axis=0)*255)
out=args.output
out.parent.mkdir(parents=True,exist_ok=True)
Image.fromarray(atlas,'RGB').save(out,optimize=True)
print(out,out.stat().st_size)
