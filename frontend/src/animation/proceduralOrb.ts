import type {CronosState} from '../types/cronos';
import {orbMotionTarget} from './orbDynamics.ts';

type SceneCanvas=HTMLCanvasElement|OffscreenCanvas;
type OrbInput={state:CronosState;audio:number;hidden:boolean;fps?:number;referenceTime?:number};
type Strand={offset:number;seed:number;width:number;opacity:number;spread?:number;led?:boolean};

const TAU=Math.PI*2;
const STEPS=480;
const ANGLES=Float32Array.from({length:STEPS+1},(_,index)=>index/STEPS*TAU);
const COS=Float32Array.from(ANGLES,angle=>Math.cos(angle));
const SIN=Float32Array.from(ANGLES,angle=>Math.sin(angle));
const RADIUS_CENTER=190;
const RADIUS_SPAN=55;
// Uneven spacing leaves visible blue gaps between the brighter LED filaments.
const backgroundOffsets=[-42,-38,-34,-29,-25,-19,-13,-8,-3,2,8,14,20,27,35,43];
const background:Strand[]=Array.from({length:16},(_,index)=>({
 offset:backgroundOffsets[index],
 seed:.6+index*1.783,
 width:.36+(index%3)*.09,
 opacity:.17+(index%5)*.018,
}));
const foreground:Strand[]=[
 {offset:-27,seed:.38,width:1.42,opacity:.68,spread:.75,led:true},
 {offset:-15,seed:2.48,width:1.08,opacity:.48},
 {offset:-3,seed:4.67,width:1.34,opacity:.64,led:true},
 {offset:12,seed:6.53,width:1.05,opacity:.43},
 {offset:26,seed:8.14,width:1.24,opacity:.53,spread:.75,led:true},
 {offset:34,seed:9.7,width:.85,opacity:.30,spread:.55},
];
// Half-second samples measured from the unobstructed speaking sequence.
// Only the light envelope repeats; the line geometry is always generated.
const SPEECH_LIGHT=[1,.68,.47,.69,.62,.42,.25,.96,.99,1,.66];
function speechLightAt(seconds:number){
 const position=(seconds*2)%SPEECH_LIGHT.length;
 const index=Math.floor(position),next=(index+1)%SPEECH_LIGHT.length;
 const t=position-index,smooth=t*t*(3-2*t);
 return SPEECH_LIGHT[index]*(1-smooth)+SPEECH_LIGHT[next]*smooth;
}

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
 const raw=(common+distance)*(1+expansion);
 const radius=RADIUS_CENTER+RADIUS_SPAN*Math.tanh((raw-RADIUS_CENTER)/RADIUS_SPAN);
 return {x:300+Math.cos(angle)*radius,y:300+Math.sin(angle)*radius};
}

function brightness(angle:number,strand:Strand,phase:number){
 return .47
  +.27*Math.sin(2*angle+strand.seed*.9+phase*.24)
  +.16*Math.sin(3*angle-strand.seed*.73-phase*.31)
  +.10*Math.sin(5*angle+strand.seed*.43+phase*.42);
}

function fillSamples(values:Float32Array,strand:Strand,common:Float32Array,phase:number,flow:number,energy:number,expansion:number){
 const motion=1+energy*.42,spread=strand.spread??1;
 for(let index=0;index<=STEPS;index++){
  const angle=ANGLES[index];
  const distance=strand.offset
   +spread*motion*24.5*Math.sin(2*angle+strand.seed+phase*.43)
   +spread*motion*11.5*Math.sin(3*angle-strand.seed*.62-phase*.34)
   +spread*6.8*Math.sin(angle+strand.seed*.48-phase*.22)
   +spread*4.6*Math.sin(5*angle+strand.seed*1.07+phase*.27)
   +1.3*Math.sin(8*angle-strand.seed*.8-phase*.29);
  const raw=(common[index]+distance)*(1+expansion);
  const radius=RADIUS_CENTER+RADIUS_SPAN*Math.tanh((raw-RADIUS_CENTER)/RADIUS_SPAN);
  const base=index*3;
  values[base]=300+COS[index]*radius;
  values[base+1]=300+SIN[index]*radius;
  values[base+2]=brightness(angle,strand,flow);
 }
}

function trace(ctx:CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D,values:Float32Array,minimum=-1){
 ctx.beginPath();let connected=false;
 for(let index=0;index<=STEPS;index++){
  const base=index*3;
  if(values[base+2]<minimum){connected=false;continue;}
  if(connected)ctx.lineTo(values[base],values[base+1]);else ctx.moveTo(values[base],values[base+1]);
  connected=true;
 }
}

function drawGlints(ctx:CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D,phase:number,flow:number,energy:number,expansion:number,ledGain:number,baseGain:number){
 for(let index=0;index<2;index++){
  const strand=background[2+index*11];
  const angle=2.2+index*1.75+flow*(.62+index*.1);
  const point=orbPoint(angle,strand,phase,energy,expansion);
  const haze=ctx.createRadialGradient(point.x,point.y,0,point.x,point.y,17);
  haze.addColorStop(0,'rgba(32,160,255,.34)');
  haze.addColorStop(1,'rgba(9,75,226,0)');
  ctx.globalAlpha=baseGain;ctx.fillStyle=haze;
  ctx.beginPath();ctx.arc(point.x,point.y,17,0,TAU);ctx.fill();
 }
 for(let index=0;index<4;index++){
  const strand=foreground[[0,2,4,2][index]];
  const angle=flow*(.64+index*.08)+index*1.81+.4;
  const point=orbPoint(angle,strand,phase,energy,expansion);
  const pulse=.72+.28*Math.sin(flow*1.15+index*1.7);
  ctx.globalAlpha=ledGain*pulse*.74;
  ctx.strokeStyle='#4ad9ff';ctx.lineWidth=.95;ctx.shadowColor='#1aa7ff';ctx.shadowBlur=6;
  ctx.beginPath();
  for(let step=0;step<=12;step++){
   const trail=orbPoint(angle-.15+step*.15/12,strand,phase,energy,expansion);
   if(step===0)ctx.moveTo(trail.x,trail.y);else ctx.lineTo(trail.x,trail.y);
  }
  ctx.stroke();ctx.shadowBlur=0;
  const glow=ctx.createRadialGradient(point.x,point.y,0,point.x,point.y,15);
  glow.addColorStop(0,'rgba(194,247,255,.92)');
  glow.addColorStop(.2,'rgba(55,218,255,.77)');
  glow.addColorStop(1,'rgba(19,129,244,0)');
  ctx.globalAlpha=ledGain*pulse;ctx.fillStyle=glow;
  ctx.beginPath();ctx.arc(point.x,point.y,15,0,TAU);ctx.fill();
  ctx.globalAlpha=ledGain*pulse*.95;ctx.fillStyle='#b9f5ff';
  ctx.beginPath();ctx.arc(point.x,point.y,.9,0,TAU);ctx.fill();
 }
}

/** Animated, resolution-independent artwork drawn in the canvas worker. */
export function renderProceduralOrb(canvas:SceneCanvas,size:number,pixelRatio:number,input:()=>OrbInput){
 let bitmap=Math.min(1080,Math.round(size*Math.min(pixelRatio,1080/size)));
 canvas.width=canvas.height=bitmap;
 const ctx=canvas.getContext('2d',{alpha:true}) as CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D|null;
 if(!ctx)return;
 ctx.setTransform(bitmap/600,0,0,bitmap/600,0,0);
 ctx.lineCap='round';ctx.lineJoin='round';
 const common=new Float32Array(STEPS+1);
 const backgroundSamples=background.map(()=>new Float32Array((STEPS+1)*3));
 const foregroundSamples=foreground.map(()=>new Float32Array((STEPS+1)*3));
 const diagnostics={frames:0,lastRenderMs:0,averageRenderMs:0,averageFrameMs:0,canvasPixels:bitmap};
 (self as typeof self&{__cronosOrbDiagnostics?:typeof diagnostics}).__cronosOrbDiagnostics=diagnostics;
 let active=true,frame=0,timer=0,last=performance.now(),phase=0,flow=0,velocity=.42,flowVelocity=.38,energy=.035,expansion=0,audioEnvelope=0,ledGain=.18,baseGain=.6,speechClock=0,previousState:CronosState='IDLE',slowFrames=0;
 const schedule=(delay=0)=>{if(!active)return;if(delay)timer=self.setTimeout(()=>{if(active)frame=requestAnimationFrame(draw);},delay);else frame=requestAnimationFrame(draw);};
 const draw=()=>{
  if(!active)return;
  const value=input(),now=performance.now();
  if(value.hidden){last=now;slowFrames=0;schedule(180);return;}
  if(now-last<1000/Math.min(value.fps||60,30)-1){schedule();return;}
  const elapsedMs=now-last;
  const dt=Math.min(.1,elapsedMs/1000);last=now;
  slowFrames=elapsedMs>43?slowFrames+1:Math.max(0,slowFrames-2);
  if(slowFrames>=9&&bitmap>600){
   bitmap=bitmap>900?900:bitmap>720?720:600;
   canvas.width=canvas.height=bitmap;
   ctx.setTransform(bitmap/600,0,0,bitmap/600,0,0);
   ctx.lineCap='round';ctx.lineJoin='round';
   diagnostics.canvasPixels=bitmap;
   slowFrames=0;
  }
  const renderStart=performance.now();
  const level=Number.isFinite(value.audio)?Math.max(0,Math.min(1,value.audio)):0;
  audioEnvelope+=(level-audioEnvelope)*Math.min(1,dt*(level>audioEnvelope?8:2.3));
  const target=orbMotionTarget(value.state,audioEnvelope);
  velocity+=(target.rate-velocity)*Math.min(1,dt*3.2);
  const flowTarget=value.state==='SPEAKING'?1.9:value.state==='LISTENING'?.75:.38;
  flowVelocity+=(flowTarget-flowVelocity)*Math.min(1,dt*3.2);
  energy+=(target.energy-energy)*Math.min(1,dt*3.6);
  expansion+=(target.expansion-expansion)*Math.min(1,dt*3);
  if(value.state==='SPEAKING'&&previousState!=='SPEAKING')speechClock=0;
  if(value.state==='SPEAKING')speechClock+=dt;
  previousState=value.state;
  const lightTarget=value.state==='SPEAKING'?( .12+.88*speechLightAt(speechClock))*(.9+.1*audioEnvelope):value.state==='LISTENING'?.35:.18;
  ledGain+=(lightTarget-ledGain)*Math.min(1,dt*6);
  baseGain+=((value.state==='SPEAKING'?1:value.state==='LISTENING'?.72:.6)-baseGain)*Math.min(1,dt*3);
  phase=Number.isFinite(value.referenceTime)?value.referenceTime!:phase+dt*velocity;
  flow=Number.isFinite(value.referenceTime)?value.referenceTime!:flow+dt*flowVelocity;
  for(let index=0;index<=STEPS;index++){
   const angle=ANGLES[index];
   common[index]=186+8.4*Math.sin(2*angle+.38+phase*.31)
    +5.7*Math.sin(3*angle-.27-phase*.23)
    +2.1*Math.sin(5*angle+phase*.17);
  }
  for(let index=0;index<background.length;index++)fillSamples(backgroundSamples[index],background[index],common,phase,flow,energy,expansion);
  for(let index=0;index<foreground.length;index++)fillSamples(foregroundSamples[index],foreground[index],common,phase,flow,energy,expansion);
  ctx.clearRect(0,0,600,600);
  ctx.save();ctx.globalCompositeOperation='screen';
  // Separated dim blue filaments remain visible behind selected LED paths.
  for(let index=0;index<background.length;index++){
   const strand=background[index],samples=backgroundSamples[index];
   trace(ctx,samples);
   ctx.globalAlpha=strand.opacity*baseGain;ctx.strokeStyle='#267de0';ctx.lineWidth=strand.width;
   ctx.stroke();
   trace(ctx,samples,.54);
   ctx.globalAlpha=strand.opacity*.65*baseGain;ctx.strokeStyle='#328ef0';ctx.stroke();
  }
  for(let index=0;index<foreground.length;index++){
   const strand=foreground[index],samples=foregroundSamples[index];
   trace(ctx,samples);
   ctx.globalAlpha=strand.opacity*.52*baseGain;ctx.strokeStyle='#168dd8';ctx.lineWidth=strand.width+.18;ctx.stroke();
   for(const [minimum,alpha] of [[.36,.39],[.56,.49],[.70,.44]] as const){
    trace(ctx,samples,minimum);
    if(minimum>=.56){
     ctx.globalAlpha=.25*ledGain;ctx.strokeStyle='#20c2ff';ctx.lineWidth=strand.width+2.8;
     ctx.shadowColor='#1398fc';ctx.shadowBlur=8;ctx.stroke();ctx.shadowBlur=0;
    }
    ctx.globalAlpha=alpha*ledGain*(strand.led?1.16:.72);
    ctx.strokeStyle=strand.led?(minimum>=.70?'#51eaff':'#38d6ff'):'#34b9ed';
    ctx.lineWidth=strand.width;
    ctx.shadowColor=minimum>=.70?'#20bcff':'transparent';ctx.shadowBlur=minimum>=.70?3:0;
    ctx.stroke();ctx.shadowBlur=0;
   }
  }
  drawGlints(ctx,phase,flow,energy,expansion,ledGain,baseGain);
  ctx.restore();
  const renderMs=performance.now()-renderStart;
  diagnostics.frames++;
  diagnostics.lastRenderMs=renderMs;
  diagnostics.averageRenderMs=diagnostics.averageRenderMs?diagnostics.averageRenderMs*.9+renderMs*.1:renderMs;
  diagnostics.averageFrameMs=diagnostics.averageFrameMs?diagnostics.averageFrameMs*.9+dt*1000*.1:dt*1000;
  schedule();
 };
 frame=requestAnimationFrame(draw);
 return ()=>{active=false;self.clearTimeout(timer);cancelAnimationFrame(frame);};
}
