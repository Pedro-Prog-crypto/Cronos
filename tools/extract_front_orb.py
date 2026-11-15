"""Preserve the photographed filaments without fitting a fixed number of curves.

Build-time input: v05/stabilized from measure_reference_motion.py.
The grid/text are rejected by chroma and an annulus, never by deleting short paths.
"""
from pathlib import Path
import argparse,json
import numpy as np
from scipy.ndimage import gaussian_filter,map_coordinates
from PIL import Image,ImageDraw

def main():
 root=Path(__file__).resolve().parents[1]
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=Path('/workspace/Cronos-reference-complete/v05/stabilized'));p.add_argument('--output',type=Path,default=root/'frontend/src/assets/images/orb-front-field.png');a=p.parse_args()
 count,angles,rows,columns=236,640,120,6
 theta=np.linspace(-np.pi,np.pi,angles,endpoint=False);radii=np.linspace(112,238,rows)
 xx=255+np.cos(theta)[None,:]*radii[:,None];yy=255-np.sin(theta)[None,:]*radii[:,None]
 fields=[];blues=[];glints=[]
 for n in range(127,363):
  rgb=np.asarray(Image.open(a.source/f'{n:05d}.jpg'),dtype=np.float32);r,g,b=rgb.transpose(2,0,1)
  # Neutral grid and editorial white lettering cancel in chroma. A broad
  # local background is removed without projecting curves onto Fourier fits.
  cyan=g-r-.08*b;blue=b-1.15*r
  cyan=np.maximum(cyan-gaussian_filter(cyan,9)*.78-2.5,0)
  blue=np.maximum(blue-gaussian_filter(blue,9)*.9-2,0)
  # Pinpoint highlights are measured in the footage, not placed on a fake orbit.
  glint=np.maximum(g-gaussian_filter(g,3)*1.2-42,0)*np.clip((g-r-12)/36,0,1)
  # Captions are burned into the filmed footage and are never part of the orb.
  cyan[470:,:]=0;blue[470:,:]=0;glint[470:,:]=0
  fields.append(map_coordinates(cyan,[yy,xx],order=1,mode='nearest'))
  blues.append(map_coordinates(blue,[yy,xx],order=1,mode='nearest'))
  glints.append(map_coordinates(glint,[yy,xx],order=1,mode='nearest'))
 def clean(values):
  values=np.asarray(values)
  # Persistent camera/monitor pattern is weaker than the moving filaments.
  baseline=np.quantile(values,.15,axis=0)
  values=np.maximum(values-baseline[None]*.2,0)
  return gaussian_filter(values,(.65,.32,.42),mode=('nearest','nearest','wrap'))
 cyan,blue=clean(fields),clean(blues)
 # Retain local radial peaks: broad screen glare and compression blocks are
 # not strands. This does not interpolate across genuine gaps in the footage.
 cyan=np.maximum(cyan-gaussian_filter(cyan,(0,3,0),mode=('nearest','nearest','wrap'))*.8-2.5,0)
 blue=np.maximum(blue-gaussian_filter(blue,(0,4,0),mode=('nearest','nearest','wrap'))*.8-3,0)
 fade=np.minimum(np.clip((radii-120)/12,0,1),np.clip((236-radii)/10,0,1))
 cyan=np.clip(cyan*fade[None,:,None]/25,0,1)**1.12
 blue=np.clip(blue*fade[None,:,None]/18,0,1)**1.08
 # A narrow radial core restores the crisp LED line washed out by filming.
 cyan=np.clip((cyan-gaussian_filter(cyan,(0,1.25,.55),mode=('nearest','nearest','wrap'))*.38)*1.75,0,1)
 glint=np.clip(np.asarray(glints)*fade[None,:,None]/35,0,1)**1.25
 glint=gaussian_filter(glint,(.35,.55,.55),mode=('nearest','nearest','wrap'))
 # Speaking and listening are separate measured sections of the reference.
 # Replaying the speaking section at idle made the home screen too restless.
 def loop(v,overlap):
  output=v[overlap:].copy();mix=np.linspace(0,1,overlap);mix=mix*mix*(3-2*mix)
  output[-overlap:]=output[-overlap:]*(1-mix[:,None,None])+v[:overlap]*mix[:,None,None]
  return output
 speaking_count,listening_count=155,45
 cyan=np.concatenate([loop(cyan[:171],16),loop(cyan[181:],10)])
 blue=np.concatenate([loop(blue[:171],16),loop(blue[181:],10)])
 glint=np.concatenate([loop(glint[:171],16),loop(glint[181:],10)])
 frames=len(cyan)
 atlas=np.zeros((((frames+columns-1)//columns)*rows,columns*angles,3),np.uint8)
 for i in range(frames):
  rgb=np.stack([cyan[i],glint[i],blue[i]],axis=-1)
  y,x=i//columns*rows,i%columns*angles;atlas[y:y+rows,x:x+angles]=np.uint8(np.clip(rgb,0,1)*255)
 a.output.parent.mkdir(exist_ok=True,parents=True);Image.fromarray(atlas).save(a.output,optimize=True)
 info=dict(frames=frames,columns=columns,angles=angles,rows=rows,width=atlas.shape[1],height=atlas.shape[0],source='v05 frames 127–362; camera-aligned',speaking_frames=speaking_count,listening_frames=listening_count,source_segments={'speaking':[127,297],'listening':[308,362]},loop_overlap_frames={'speaking':16,'listening':10},curve_fitting=False)
 a.output.with_suffix('.json').write_text(json.dumps(info,indent=2))
 # Decode diagnostic samples through the same polar mapping as the renderer.
 size=510;gy,gx=np.mgrid[:size,:size];radius=np.hypot(gx-255,gy-255);azimuth=(np.arctan2(-(gy-255),gx-255)+np.pi)/(2*np.pi)*angles
 radial=(radius-112)/126*(rows-1);band=(radial>=0)&(radial<rows-1)
 sheet=Image.new('RGB',(size*3,(size+25)*2),'#03152e');d=ImageDraw.Draw(sheet)
 for j,i in enumerate([0,29,53,100,160,199]):
  c=map_coordinates(cyan[i],[radial,azimuth],order=1,mode='grid-wrap')*band;bl=map_coordinates(blue[i],[radial,azimuth],order=1,mode='grid-wrap')*band
  rgb=np.stack([c*.12,c*.75+bl*.10,c*.96+bl*.64],-1)
  rgb=np.maximum(rgb,np.array([.01,.04,.10]));im=Image.fromarray(np.uint8(np.clip(rgb,0,1)*255))
  x,y=j%3*size,j//3*(size+25);sheet.paste(im,(x,y));d.text((x+8,y+size+4),f'Atlas frame {i}',fill='white')
 out=root/'docs/visual-audit-r55';out.mkdir(exist_ok=True);sheet.save(out/'field-samples.jpg',quality=94)
 print(json.dumps(info))

if __name__=='__main__':main()
