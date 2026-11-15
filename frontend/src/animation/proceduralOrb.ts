import type {CronosState} from '../types/cronos';
import {orbMotionTarget} from './orbDynamics';

type SceneCanvas=HTMLCanvasElement|OffscreenCanvas;
type OrbInput={state:CronosState;audio:number;hidden:boolean;fps?:number;referenceTime?:number};
type Strand={offset:number;seed:number;width:number;opacity:number;spread?:number;led?:boolean};

const TAU=Math.PI*2;
const STEPS=480;
const background:Strand[]=Array.from({length:16},(_,index)=>({
 offset:(index-7.5)*4.7,
 seed:.6+index*1.783,
 width:.36+(index%3)*.09,
 opacity:.17+(index%5)*.018,
}));
const foreground:Strand[]=[
 {offset:-27,seed:.38,width:1.12,opacity:.68,spread:.75,led:true},
 {offset:-15,seed:2.48,width:.96,opacity:.48},
 {offset:-3,seed:4.67,width:1.04,opacity:.64,led:true},
 {offset:12,seed:6.53,width:.92,opacity:.43},
 {offset:26,seed:8.14,width:.84,opacity:.53,spread:.75,led:true},
 {offset:34,seed:9.7,width:.68,opacity:.30,spread:.55},
];

/** Independent filaments share a slow deformation field, but never a texture. */
export function orbPoint(angle:number,strand:Strand,phase:number,energy:number,expansion:number){
 const motion=1+energy*.42;
 const spread=strand.spread??1;
 const common=186
  +8.4*Math.sin(2*angle+.38+phase*.31)
  +5.7*Math.sin(3*angle-.27-phase*.23)
  +2.1*Math.sin(5*angle+phase*.17);
 const distance=strand.offset
  +spread*motion*24.5*Math.sin(2*angle+strand.seed+phase*.43)
  +spread*motion*11.5*Math.sin(3*angle-strand.seed*.62-phase*.34)
  +spread*6.8*Math.sin(angle+strand.seed*.48-phase*.22)
  +spread*4.6*Math.sin(5*angle+strand.seed*1.07+phase*.27)
  +1.3*Math.sin(8*angle-strand.seed*.8-phase*.29);
 const radius=(common+distance)*(1+expansion);
 return {x:300+Math.cos(angle)*radius,y:300+Math.sin(angle)*radius};
}

function brightness(angle:number,strand:Strand,phase:number){
 return .47
  +.27*Math.sin(2*angle+strand.seed*.9+phase*.24)
  +.16*Math.sin(3*angle-strand.seed*.73-phase*.31)
  +.10*Math.sin(5*angle+strand.seed*.43+phase*.42);
}

function trace(ctx:CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D,strand:Strand,phase:number,energy:number,expansion:number,minimum=-1){
 ctx.beginPath();let connected=false;
 for(let index=0;index<=STEPS;index++){
  const angle=index/STEPS*TAU;
  if(brightness(angle,strand,phase)<minimum){connected=false;continue;}
  const point=orbPoint(angle,strand,phase,energy,expansion);
  if(connected)ctx.lineTo(point.x,point.y);else ctx.moveTo(point.x,point.y);
  connected=true;
 }
}

function drawGlints(ctx:CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D,phase:number,energy:number,expansion:number,gain:number){
 for(let index=0;index<2;index++){
  const strand=background[2+index*11];
  const angle=2.2+index*1.75+phase*(.62+index*.1);
  const point=orbPoint(angle,strand,phase,energy,expansion);
  const haze=ctx.createRadialGradient(point.x,point.y,0,point.x,point.y,17);
  haze.addColorStop(0,'rgba(32,160,255,.34)');
  haze.addColorStop(1,'rgba(9,75,226,0)');
  ctx.globalAlpha=gain;ctx.fillStyle=haze;
  ctx.beginPath();ctx.arc(point.x,point.y,17,0,TAU);ctx.fill();
 }
 for(let index=0;index<4;index++){
  const strand=foreground[[0,2,4,2][index]];
  const angle=phase*(1.12+index*.13)+index*1.81+.4;
  const point=orbPoint(angle,strand,phase,energy,expansion);
  const pulse=.72+.28*Math.sin(phase*2.1+index*1.7);
  ctx.globalAlpha=gain*pulse*.62;
  ctx.strokeStyle='#4ad9ff';ctx.lineWidth=.95;ctx.shadowColor='#1aa7ff';ctx.shadowBlur=6;
  ctx.beginPath();
  for(let step=0;step<=12;step++){
   const trail=orbPoint(angle-.15+step*.15/12,strand,phase,energy,expansion);
   if(step===0)ctx.moveTo(trail.x,trail.y);else ctx.lineTo(trail.x,trail.y);
  }
  ctx.stroke();ctx.shadowBlur=0;
  const glow=ctx.createRadialGradient(point.x,point.y,0,point.x,point.y,10);
  glow.addColorStop(0,'rgba(194,247,255,.92)');
  glow.addColorStop(.2,'rgba(55,218,255,.77)');
  glow.addColorStop(1,'rgba(19,129,244,0)');
  ctx.globalAlpha=gain*pulse;ctx.fillStyle=glow;
  ctx.beginPath();ctx.arc(point.x,point.y,10,0,TAU);ctx.fill();
  ctx.globalAlpha=gain*pulse*.95;ctx.fillStyle='#b9f5ff';
  ctx.beginPath();ctx.arc(point.x,point.y,.9,0,TAU);ctx.fill();
 }
}

/** Animated, resolution-independent artwork drawn in the canvas worker. */
export function renderProceduralOrb(canvas:SceneCanvas,size:number,pixelRatio:number,input:()=>OrbInput){
 const bitmap=Math.min(1080,Math.round(size*Math.min(pixelRatio,1080/size)));
 canvas.width=canvas.height=bitmap;
 const ctx=canvas.getContext('2d',{alpha:true}) as CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D|null;
 if(!ctx)return;
 ctx.setTransform(bitmap/600,0,0,bitmap/600,0,0);
 ctx.lineCap='round';ctx.lineJoin='round';
 let active=true,frame=0,timer=0,last=performance.now(),phase=0,velocity=.42,energy=.035,expansion=0,audioEnvelope=0,gain=.8;
 const schedule=(delay=0)=>{if(!active)return;if(delay)timer=self.setTimeout(()=>{if(active)frame=requestAnimationFrame(draw);},delay);else frame=requestAnimationFrame(draw);};
 const draw=()=>{
  if(!active)return;
  const value=input(),now=performance.now();
  if(value.hidden){last=now;schedule(180);return;}
  if(now-last<1000/Math.min(value.fps||60,bitmap>=1000?30:60)-1){schedule();return;}
  const dt=Math.min(.1,(now-last)/1000);last=now;
  const level=Number.isFinite(value.audio)?Math.max(0,Math.min(1,value.audio)):0;
  audioEnvelope+=(level-audioEnvelope)*Math.min(1,dt*(level>audioEnvelope?8:2.3));
  const target=orbMotionTarget(value.state,audioEnvelope);
  velocity+=(target.rate-velocity)*Math.min(1,dt*3.2);
  energy+=(target.energy-energy)*Math.min(1,dt*3.6);
  expansion+=(target.expansion-expansion)*Math.min(1,dt*3);
  gain+=((value.state==='SPEAKING'?1:value.state==='LISTENING'?.9:.78)-gain)*Math.min(1,dt*4);
  phase=Number.isFinite(value.referenceTime)?value.referenceTime!:phase+dt*velocity;
  ctx.clearRect(0,0,600,600);
  ctx.save();ctx.globalCompositeOperation='screen';
  // Separated dim blue filaments remain visible behind selected LED paths.
  for(const strand of background){
   trace(ctx,strand,phase,energy,expansion);
   ctx.globalAlpha=strand.opacity*gain;ctx.strokeStyle='#267de0';ctx.lineWidth=strand.width;
   ctx.stroke();
   trace(ctx,strand,phase,energy,expansion,.54);
   ctx.globalAlpha=strand.opacity*.65*gain;ctx.strokeStyle='#328ef0';ctx.stroke();
  }
  for(const strand of foreground){
   trace(ctx,strand,phase,energy,expansion);
   ctx.globalAlpha=strand.opacity*.52*gain;ctx.strokeStyle='#168dd8';ctx.lineWidth=strand.width+.18;ctx.stroke();
   for(const [minimum,alpha] of [[.36,.39],[.56,.49],[.70,.44]] as const){
    trace(ctx,strand,phase,energy,expansion,minimum);
    if(minimum>=.56){
     ctx.globalAlpha=.13*gain;ctx.strokeStyle='#21bbff';ctx.lineWidth=strand.width+2.2;
     ctx.shadowColor='#1398fc';ctx.shadowBlur=6;ctx.stroke();ctx.shadowBlur=0;
    }
    ctx.globalAlpha=alpha*gain*(strand.led?1.16:.72);
    ctx.strokeStyle=strand.led?(minimum>=.70?'#d0f8ff':'#49d9ff'):'#34b9ed';
    ctx.lineWidth=strand.width;
    ctx.shadowColor=minimum>=.70?'#20bcff':'transparent';ctx.shadowBlur=minimum>=.70?3:0;
    ctx.stroke();ctx.shadowBlur=0;
   }
  }
  drawGlints(ctx,phase,energy,expansion,gain);
  ctx.restore();schedule();
 };
 frame=requestAnimationFrame(draw);
 return ()=>{active=false;self.clearTimeout(timer);cancelAnimationFrame(frame);};
}
