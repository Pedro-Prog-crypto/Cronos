"""Preserve the photographed filaments without fitting a fixed number of curves.

Build-time input: v05/stabilized from measure_reference_motion.py.
The grid/text are rejected by chroma and an annulus, never by deleting short paths.
"""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.ndimage import gaussian_filter,map_coordinates,maximum_filter
from PIL import Image,ImageDraw

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=Path('/workspace/Cronos-reference-complete/v05/stabilized'));p.add_argument('--output',type=Path,default=Path('/workspace/Cronos/frontend/src/assets/images/orb-front-field.png'));a=p.parse_args()
 count,angles,rows,columns=236,640,96,6
 theta=np.linspace(-np.pi,np.pi,angles,endpoint=False);radii=np.linspace(112,238,rows)
 xx=255+np.cos(theta)[None,:]*radii[:,None];yy=255-np.sin(theta)[None,:]*radii[:,None]
 fields=[];blues=[]
 for n in range(127,363):
  rgb=np.asarray(Image.open(a.source/f'{n:05d}.jpg'),dtype=np.float32);r,g,b=rgb.transpose(2,0,1)
  # Neutral grid and editorial white lettering cancel in chroma. A broad
  # local background is removed without projecting curves onto Fourier fits.
  cyan=g-r-.08*b;blue=b-1.15*r
  cyan=np.maximum(cyan-gaussian_filter(cyan,6)-.6,0)
  blue=np.maximum(blue-gaussian_filter(blue,8),0)
  # Captions are burned into the filmed footage and are never part of the orb.
  cyan[457:,:]=0;blue[457:,:]=0
  fields.append(map_coordinates(cyan,[yy,xx],order=1,mode='nearest'))
  blues.append(map_coordinates(blue,[yy,xx],order=1,mode='nearest'))
 def clean(values):
  values=np.asarray(values)
  # Persistent camera/monitor pattern is weaker than the moving filaments.
  baseline=np.quantile(values,.15,axis=0)
  values=np.maximum(values-baseline[None]*.2,0)
  return gaussian_filter(values,(.30,.30,.38),mode=('nearest','nearest','wrap'))
 cyan,blue=clean(fields),clean(blues)
 # Retain local radial peaks: broad screen glare and compression blocks are
 # not strands. This does not interpolate across genuine gaps in the footage.
 cyan=np.maximum(cyan-3.5,0);blue=np.maximum(blue-9,0)
 cyan*=np.clip((cyan/(maximum_filter(cyan,size=(1,11,1))+1e-4)-.35)/.65,0,1)
 blue*=np.clip((blue/(maximum_filter(blue,size=(1,13,1))+1e-4)-.35)/.65,0,1)
 fade=np.minimum(np.clip((radii-120)/12,0,1),np.clip((236-radii)/10,0,1))
 cyan=np.clip(cyan*fade[None,:,None]/31,0,1)**.9
 blue=np.clip(blue*fade[None,:,None]/24,0,1)**.85
 # A short crossfade is explicit and auditable, not claimed as original motion.
 overlap=24;frames=count-overlap
 def loop(v):
  output=v[overlap:].copy();mix=np.linspace(0,1,overlap);mix=mix*mix*(3-2*mix)
  output[-overlap:]=output[-overlap:]*(1-mix[:,None,None])+v[:overlap]*mix[:,None,None]
  return output
 cyan,blue=loop(cyan),loop(blue)
 atlas=np.zeros((((frames+columns-1)//columns)*rows,columns*angles,3),np.uint8)
 for i in range(frames):
  halo=gaussian_filter(cyan[i],(.9,1.1),mode=('nearest','wrap'))
  rgb=np.stack([cyan[i],halo,blue[i]],axis=-1)
  y,x=i//columns*rows,i%columns*angles;atlas[y:y+rows,x:x+angles]=np.uint8(np.clip(rgb,0,1)*255)
 a.output.parent.mkdir(exist_ok=True,parents=True);Image.fromarray(atlas).save(a.output,optimize=True)
 info=dict(frames=frames,columns=columns,angles=angles,rows=rows,width=atlas.shape[1],height=atlas.shape[0],duration=frames/30,source='v05 frames 127–362; camera-aligned',loop_overlap_frames=overlap,curve_fitting=False)
 a.output.with_suffix('.json').write_text(json.dumps(info,indent=2))
 # Decode diagnostic samples through the same polar mapping as the renderer.
 size=510;gy,gx=np.mgrid[:size,:size];radius=np.hypot(gx-255,gy-255);azimuth=(np.arctan2(-(gy-255),gx-255)+np.pi)/(2*np.pi)*angles
 radial=(radius-112)/126*(rows-1);band=(radial>=0)&(radial<rows-1)
 sheet=Image.new('RGB',(size*3,(size+25)*2),'#03152e');d=ImageDraw.Draw(sheet)
 for j,i in enumerate([0,29,53,100,160,211]):
  c=map_coordinates(cyan[i],[radial,azimuth],order=1,mode='grid-wrap')*band;bl=map_coordinates(blue[i],[radial,azimuth],order=1,mode='grid-wrap')*band
  rgb=np.stack([c*.12,c*.75+bl*.10,c*.96+bl*.64],-1)
  rgb=np.maximum(rgb,np.array([.01,.04,.10]));im=Image.fromarray(np.uint8(np.clip(rgb,0,1)*255))
  x,y=j%3*size,j//3*(size+25);sheet.paste(im,(x,y));d.text((x+8,y+size+4),f'Atlas frame {i}',fill='white')
 out=Path('/workspace/Cronos/docs/visual-audit-r52');out.mkdir(exist_ok=True);sheet.save(out/'field-samples.jpg',quality=94)
 print(json.dumps(info))

if __name__=='__main__':main()
