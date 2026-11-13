import {CronosState} from '../types/cronos';
import framesAUrl from '../assets/images/hologram-reference-frames-a.png?url';
import framesBUrl from '../assets/images/hologram-reference-frames-b.jpg?url';
export type SceneInput={state:CronosState;audio:number;hidden:boolean;links:boolean;fps?:number};
type SceneCanvas=HTMLCanvasElement|OffscreenCanvas;
function context(canvas:SceneCanvas){return canvas.getContext('2d') as CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D|null;}
function buffer():SceneCanvas{return typeof OffscreenCanvas!=='undefined'?new OffscreenCanvas(600,600):document.createElement('canvas');}
let orbFramesPromise:Promise<SceneCanvas[]>|undefined;
function orbFrames(){
 if(orbFramesPromise)return orbFramesPromise;
 orbFramesPromise=(async()=>{
  const sources=await Promise.all([framesAUrl,framesBUrl].map(async url=>{
   const response=await fetch(url);if(!response.ok)throw new Error(`Hologram frame ${response.status}`);
   return createImageBitmap(await response.blob());
  }));
  const edgeMask=new Uint8Array(600*600);
  for(let pixel=0;pixel<edgeMask.length;pixel++){
   const x=pixel%600-300,y=Math.floor(pixel/600)-300;
   edgeMask[pixel]=Math.round(255*Math.max(0,Math.min(1,(290-Math.hypot(x,y))/20)));
  }
  const frames:SceneCanvas[]=[];
  try{
   for(const source of sources){
    const cellWidth=source.width/3,cellHeight=source.height/2;
    for(let index=0;index<6;index++){
     const frame=buffer();frame.width=frame.height=600;
     const target=context(frame)!;
     target.drawImage(source,(index%3)*cellWidth,Math.floor(index/3)*cellHeight,cellWidth,cellHeight,0,0,600,600);
     // Black is the sprite sheet's background. Convert it to transparent light
     // so the real CRONOS scene stays visible behind the animated filaments.
     const pixels=target.getImageData(0,0,600,600),data=pixels.data;
     for(let i=0;i<data.length;i+=4){
      const peak=Math.max(data[i],data[i+1],data[i+2]);
      const edge=edgeMask[i/4]/255;
      if(peak<20||edge===0){data[i]=data[i+1]=data[i+2]=data[i+3]=0;continue;}
      data[i]=Math.min(255,Math.round(data[i]*255/peak));
      data[i+1]=Math.min(255,Math.round(data[i+1]*255/peak));
      data[i+2]=Math.min(255,Math.round(data[i+2]*255/peak));
      data[i+3]=Math.round((peak-20)/235*255*edge);
     }
     target.putImageData(pixels,0,0);frames.push(frame);
    }
   }
  }finally{sources.forEach(source=>source.close());}
  return frames;
 })().catch(error=>{orbFramesPromise=undefined;throw error;});
 return orbFramesPromise;
}
export function renderOrb(canvas:SceneCanvas,size:number,_density:number,pixelRatio:number,input:()=>SceneInput){
 const ctx=context(canvas);if(!ctx)return;
 const logical=600,ratio=Math.min(pixelRatio,900/size),bitmap=Math.min(900,Math.round(size*ratio)),scale=bitmap/logical;
 canvas.width=canvas.height=bitmap;ctx.setTransform(scale,0,0,scale,0,0);
 // Independent, flowing filaments. No flattened image or full-ring bloom.
 const count=8,steps=192,segments=32,segmentLength=steps/segments;
 const basis=Array.from({length:steps+1},(_,i)=>{const u=i/steps*Math.PI*2;return {u,c:Math.cos(u),s:Math.sin(u)};});
 const points=Array.from({length:count},()=>new Float32Array((steps+1)*2));
 let active=true,frame=0,timer=0,last=performance.now(),spin=0,energy=0,velocity=.28;
 let atlas:SceneCanvas[]|undefined,sequencePosition=0,previousPosition=0,transition=1;
 type OrbMode='IDLE'|'LISTENING'|'SPEAKING';
 let currentMode:OrbMode='IDLE',previousMode:OrbMode='IDLE';
 const sequences={IDLE:[0,1,2,3,4,5,4,3,2,1],LISTENING:[2,3,4,5,6,7,8,7,6,5,4,3],SPEAKING:[8,9,10,11,10,9,8,11,10,9]};
 void orbFrames().then(loaded=>{if(active)atlas=loaded;}).catch(error=>console.warn('Hologram atlas unavailable; using vector fallback.',error));
 const schedule=(delay=0)=>{if(!active)return;if(delay)timer=self.setTimeout(()=>{if(active)frame=requestAnimationFrame(draw);},delay);else frame=requestAnimationFrame(draw);};
 const trace=(target:CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D,p:Float32Array)=>{target.beginPath();target.moveTo(p[0],p[1]);for(let j=2;j<p.length;j+=2)target.lineTo(p[j],p[j+1]);target.closePath();};
 const traceSegment=(p:Float32Array,start:number,end:number)=>{ctx.beginPath();ctx.moveTo(p[start*2],p[start*2+1]);for(let j=start+1;j<=end;j++)ctx.lineTo(p[j*2],p[j*2+1]);};
 const paintSequence=(mode:typeof currentMode,position:number,opacity:number)=>{
  const sequence=sequences[mode],part=position%sequence.length,index=Math.floor(part);
  // Keep a single reference frame sharp for most of its life. Only dissolve
  // briefly at the cut; continuously blending two rings doubles the filaments.
  const fade=Math.max(0,Math.min(1,(part-index-.78)/.22));
  ctx.globalAlpha=opacity*(1-fade);ctx.drawImage(atlas![sequence[index]],0,0,logical,logical);
  if(fade>0){ctx.globalAlpha=opacity*fade;ctx.drawImage(atlas![sequence[(index+1)%sequence.length]],0,0,logical,logical);}
 };
 const draw=()=>{
  if(!active)return;const value=input(),now=performance.now();
  if(value.hidden){last=now;schedule(180);return;}
  if(now-last<1000/(value.fps||30)-1){schedule();return;}
  const dt=Math.min(.06,(now-last)/1000);last=now;
  const level=Math.max(0,Math.min(1,value.audio));
  const targetEnergy=value.state==='SPEAKING'?.72+level*.22:value.state==='LISTENING'?.35+level*.2:.06;
  const targetVelocity=value.state==='SPEAKING'?.92+level*.2:value.state==='LISTENING'?.55+level*.08:.28;
  energy+=(targetEnergy-energy)*Math.min(1,dt*4);
  velocity+=(targetVelocity-velocity)*Math.min(1,dt*3);
  spin+=dt*velocity;
  const requestedMode=value.state==='SPEAKING'?'SPEAKING':value.state==='LISTENING'?'LISTENING':'IDLE';
  if(requestedMode!==currentMode){previousMode=currentMode;previousPosition=sequencePosition;currentMode=requestedMode;sequencePosition=0;transition=0;}
  sequencePosition+=dt*(currentMode==='SPEAKING'?10+level*2:currentMode==='LISTENING'?7+level:4);
  transition=Math.min(1,transition+dt*4);
  if(atlas){
   ctx.clearRect(0,0,logical,logical);
   ctx.save();
   const wobble=energy*.025;
   ctx.translate(300,300);ctx.scale(1+Math.sin(spin*1.7)*wobble,1+Math.cos(spin*1.3)*wobble);ctx.translate(-300,-300);
   if(transition<1)paintSequence(previousMode,previousPosition,1-transition);
   const glint=Math.pow(Math.max(0,Math.sin(now/1000*(currentMode==='SPEAKING'?2.7:1.55))),8);
   const base=currentMode==='IDLE'?.78:currentMode==='LISTENING'?.83:.86;
   paintSequence(currentMode,sequencePosition,transition*Math.min(1,base+glint*.2+level*.07));
   ctx.restore();schedule();return;
  }
  ctx.clearRect(0,0,logical,logical);
  const radius=193+Math.sin(spin*.7)*2+energy*5;
  for(let k=0;k<count;k++){
   const phase=k*Math.PI*2/count,p=points[k];
   for(let i=0;i<=steps;i++){
    const {u,c,s}=basis[i];
    const r=radius+(k-(count-1)/2)*.65
      +Math.sin(2*u+phase+spin)*(19+energy*12)
      +Math.sin(u+phase*.85-spin*.4)*(7+energy*6)
      +Math.sin(3*u-phase*.7+spin*.65)*(3+energy*2);
    p[i*2]=300+c*r*(1+Math.cos(phase)*.007);
    p[i*2+1]=300+s*r*(.99+Math.sin(phase)*.009);
   }
  }
  ctx.save();ctx.lineJoin='round';ctx.lineCap='round';
  // Thin continuous paths preserve the ring silhouette between luminous regions.
  for(let k=0;k<count;k++){
   trace(ctx,points[k]);ctx.strokeStyle=k%2?'rgba(0,125,238,.48)':'rgba(0,198,255,.52)';ctx.lineWidth=1.45;ctx.stroke();
  }
  for(let k=0;k<count;k++){
   const p=points[k],phase=k*Math.PI*2/count;
   for(let slice=0;slice<segments;slice++){
    const start=slice*segmentLength,end=start+segmentLength;
    const u=(start+end)*.5/steps*Math.PI*2;
    const bright=Math.pow(Math.max(0,Math.cos(3*u-spin*.8+phase*.44)),3);
    const secondary=Math.pow(Math.max(0,Math.cos(2*u+spin*.5-phase*.6)),4)*.7;
    const intensity=Math.min(1,bright+secondary);
    if(intensity<.045)continue;
    traceSegment(p,start,end);
    if(intensity>.5){
     ctx.strokeStyle=`rgba(0,170,255,${((intensity-.5)*1.05).toFixed(3)})`;
     ctx.lineWidth=9;ctx.stroke();
    }
    ctx.strokeStyle=`rgba(0,145,255,${(.06+.17*intensity).toFixed(3)})`;
    ctx.lineWidth=3+intensity*2;ctx.stroke();
    ctx.strokeStyle=k%3===0?`rgba(211,249,255,${(.18+.78*intensity).toFixed(3)})`:`rgba(25,213,255,${(.16+.74*intensity).toFixed(3)})`;
    ctx.lineWidth=1.4+intensity*1.2+energy*.25;ctx.stroke();
   }
  }
  ctx.restore();schedule();
 };
 frame=requestAnimationFrame(draw);
 return ()=>{active=false;self.clearTimeout(timer);cancelAnimationFrame(frame);};
}

export function renderStar(canvas:SceneCanvas,size:number,weaveDensity:number,pixelRatio:number,input:()=>SceneInput){
    const ctx = context(canvas);
    if (!ctx) return;

    let animId: number;
    let timer = 0;
    let active = true;
    let previousFrame = performance.now();
    // Ceder tempo aos controles; preservar todos os filamentos, brilho e geometria.
    function schedule(delay = 0) {
      if (delay) timer = self.setTimeout(() => { if (active) animId = requestAnimationFrame(render); }, delay);
      else if (active) animId = requestAnimationFrame(render);
    }
    const width = 600, height = 600;
    // Match bitmap to displayed size; preserve original geometry in logical coordinates.
    const renderScale = Math.min(600, Math.ceil(size * Math.min(pixelRatio, 1.25))) / 600;
    canvas.width = Math.ceil(width * renderScale);canvas.height = Math.ceil(height * renderScale);
    ctx.setTransform(renderScale,0,0,renderScale,0,0);
    const cx = width / 2;
    const cy = height / 2;

    let time = 0;
    const baseRadius = 48;

    // Pre-generate 150 fine needle rays for the corona (reproducing image.png dense star spikes)
    const rayData: Array<{ angle: number; lengthFactor: number; width: number; alphaBase: number; speed: number }> = [];
    for (let i = 0; i < 150; i++) {
      const angle = (i / 150) * Math.PI * 2;
      const lengthFactor = 0.85 + ((i * 17) % 23) / 23 * 0.75 + (i % 5 === 0 ? 0.6 : 0);
      const width = i % 4 === 0 ? 1.8 : i % 2 === 0 ? 1.1 : 0.65;
      const alphaBase = 0.38 + ((i * 13) % 19) / 19 * 0.48;
      const speed = 1.2 + (i % 7) * 0.3;
      rayData.push({ angle, lengthFactor, width, alphaBase, speed });
    }

    // Pre-generate scattered cosmic stardust particles around the star (like in image.png)
    const stardust: Array<{ x: number; y: number; r: number; alpha: number; pulseSpeed: number }> = [];
    for (let i = 0; i < 75; i++) {
      const angle = Math.random() * Math.PI * 2;
      const dist = 35 + Math.pow(Math.random(), 1.6) * 210;
      stardust.push({
        x: cx + Math.cos(angle) * dist,
        y: cy + Math.sin(angle) * dist,
        r: 0.6 + Math.random() * 1.4,
        alpha: 0.35 + Math.random() * 0.65,
        pulseSpeed: 1 + Math.random() * 3,
      });
    }

    function render() {
      if (!ctx || !active) return;
      if (input().hidden || (typeof HTMLCanvasElement!=='undefined'&&canvas instanceof HTMLCanvasElement&&canvas.getClientRects().length===0)) {
        previousFrame = performance.now(); schedule(150); return;
      }
      const now = performance.now();
      if (now - previousFrame < 1000 / (input().fps || 30) - 1) { schedule(); return; }
      const frameDelta = Math.min(3, Math.max(.5, (now - previousFrame) / (1000 / 60)));
      previousFrame = now;
      ctx.clearRect(0, 0, width, height);

      const currentState = input().state;
      const currentAudio = input().audio;

      // ============================================================
      // SUAVE ONDULAÇÃO DE INTENSIDADE DA LUZ (Indo e Voltando)
      // "ela vai ficando fraca e vai ficando forte... apaga um pouquinho assim,
      // tipo uma animação dela indo e voltando, mantendo o tom"
      // Smooth sinusoidal breathing between ~0.68 (slightly dimmer) and 1.0 (full brightness)
      // ============================================================
      const breathingWave = 0.5 + 0.5 * Math.sin(time * 1.8); // 0.0 to 1.0
      // Light intensity ranges from 0.68 to 1.00 in idle, with voice adding a subtle responsive lift
      const baseIntensity = 0.68 + 0.32 * breathingWave;
      const voiceBoost = currentState === 'SPEAKING' ? 0.15 + currentAudio * 0.15 : 0;
      const light = Math.min(1.15, baseIntensity + voiceBoost);

      time += (currentState === 'SPEAKING' ? 0.024 : 0.014) * frameDelta;

      ctx.save();

      // ============================================================
      // 1. DIAGONAL COSMIC MILKY WAY NEBULA TAIL (As in image.png)
      // ============================================================
      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      ctx.translate(cx, cy);
      ctx.rotate(0.55); // ~32 degrees diagonal angle

      const nebulaGrad = ctx.createRadialGradient(30, 0, 12, 35, 0, 210);
      nebulaGrad.addColorStop(0, `rgba(190, 240, 255, ${0.42 * light})`);
      nebulaGrad.addColorStop(0.25, `rgba(110, 210, 255, ${0.26 * light})`);
      nebulaGrad.addColorStop(0.55, `rgba(35, 120, 200, ${0.14 * light})`);
      nebulaGrad.addColorStop(0.85, 'rgba(10, 45, 130, 0.04)');
      nebulaGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

      ctx.beginPath();
      ctx.ellipse(35, 0, 195, 54, 0, 0, Math.PI * 2);
      ctx.fillStyle = nebulaGrad;
      ctx.fill();
      ctx.restore();

      // ============================================================
      // 2. SCATTERED TWINKLING STARDUST PARTICLES (image.png starfield)
      // ============================================================
      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      stardust.forEach((p) => {
        const twinkle = 0.6 + 0.4 * Math.sin(time * p.pulseSpeed);
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(225, 248, 255, ${p.alpha * twinkle * light})`;
        ctx.shadowColor = '#00f0ff';
        ctx.shadowBlur = 0;
        ctx.fill();
      });
      ctx.restore();

      // ============================================================
      // 3. WIDE AMBIENT RADIANT CORE GLARE (Volumetric Bloom)
      // Smoothly breathes between slightly dimmer and stronger
      // ============================================================
      ctx.save();
      ctx.globalCompositeOperation = 'screen';

      const outerHalo = ctx.createRadialGradient(cx, cy, 2, cx, cy, baseRadius * 3.3);
      outerHalo.addColorStop(0, `rgba(255, 255, 255, ${0.98 * light})`);
      outerHalo.addColorStop(0.14, `rgba(210, 248, 255, ${0.85 * light})`);
      outerHalo.addColorStop(0.36, `rgba(56, 189, 248, ${0.48 * light})`);
      outerHalo.addColorStop(0.68, `rgba(2, 100, 230, ${0.18 * light})`);
      outerHalo.addColorStop(1, 'rgba(0, 0, 0, 0)');

      ctx.beginPath();
      ctx.arc(cx, cy, baseRadius * 3.3, 0, Math.PI * 2);
      ctx.fillStyle = outerHalo;
      ctx.fill();

      // ============================================================
      // 4. DENSE FINE RADIAL NEEDLES / CORONA SPIKES (image.png)
      // ============================================================
      const coronaBaseRadius = baseRadius * 1.05;
      rayData.forEach((ray) => {
        const dynamicLength =
          coronaBaseRadius *
          (1.0 + ray.lengthFactor * 0.68 + Math.sin(time * ray.speed + ray.angle * 4) * 0.1);
        const dynamicAlpha =
          ray.alphaBase *
          (0.75 + 0.25 * Math.sin(time * ray.speed)) *
          light;

        const x2 = cx + Math.cos(ray.angle) * dynamicLength;
        const y2 = cy + Math.sin(ray.angle) * dynamicLength;

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = `rgba(235, 252, 255, ${Math.min(1, dynamicAlpha)})`;
        ctx.lineWidth = ray.width;
        ctx.shadowColor = '#7dd3fc';
        ctx.shadowBlur = 0;
        ctx.stroke();
      });

      // ============================================================
      // 5. TRANSLUCENT CELESTIAL CIRCULAR SPHERICAL SHELL RING
      // ============================================================
      ctx.beginPath();
      ctx.arc(cx, cy, coronaBaseRadius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255, 255, 255, ${0.85 * light})`;
      ctx.lineWidth = 2.0;
      ctx.shadowColor = '#38bdf8';
      ctx.shadowBlur = (14 * light) * renderScale;
      ctx.stroke();

      // Soft second outer rim
      ctx.beginPath();
      ctx.arc(cx, cy, coronaBaseRadius + 2.5, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(125, 211, 252, ${0.55 * light})`;
      ctx.lineWidth = 1.0;
      ctx.stroke();

      // ============================================================
      // 6. PROMINENT 4-POINT DIFFRACTION SPIKES (The signature cross of image.png)
      // Horizontal and vertical spikes smoothly wax and wane with the light
      // ============================================================
      const horizSpikeLen = baseRadius * 4.8;
      const vertSpikeLen = baseRadius * 3.1;

      // Horizontal wide spike (very prominent in image.png)
      const hGrad = ctx.createLinearGradient(cx - horizSpikeLen, cy, cx + horizSpikeLen, cy);
      hGrad.addColorStop(0, 'rgba(255, 255, 255, 0)');
      hGrad.addColorStop(0.35, `rgba(125, 211, 252, ${0.48 * light})`);
      hGrad.addColorStop(0.5, `rgba(255, 255, 255, ${0.98 * light})`);
      hGrad.addColorStop(0.65, `rgba(125, 211, 252, ${0.48 * light})`);
      hGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.beginPath();
      ctx.moveTo(cx - horizSpikeLen, cy);
      ctx.lineTo(cx, cy - 3.8);
      ctx.lineTo(cx + horizSpikeLen, cy);
      ctx.lineTo(cx, cy + 3.8);
      ctx.closePath();
      ctx.fillStyle = hGrad;
      ctx.fill();

      // Sharp central horizontal laser line
      ctx.beginPath();
      ctx.moveTo(cx - horizSpikeLen * 0.96, cy);
      ctx.lineTo(cx + horizSpikeLen * 0.96, cy);
      ctx.strokeStyle = `rgba(255, 255, 255, ${light})`;
      ctx.lineWidth = 2.0;
      ctx.shadowColor = '#00f0ff';
      ctx.shadowBlur = (18 * light) * renderScale;
      ctx.stroke();

      // Vertical spike
      const vGrad = ctx.createLinearGradient(cx, cy - vertSpikeLen, cx, cy + vertSpikeLen);
      vGrad.addColorStop(0, 'rgba(255, 255, 255, 0)');
      vGrad.addColorStop(0.35, `rgba(125, 211, 252, ${0.42 * light})`);
      vGrad.addColorStop(0.5, `rgba(255, 255, 255, ${0.95 * light})`);
      vGrad.addColorStop(0.65, `rgba(125, 211, 252, ${0.42 * light})`);
      vGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.beginPath();
      ctx.moveTo(cx, cy - vertSpikeLen);
      ctx.lineTo(cx - 2.8, cy);
      ctx.lineTo(cx + vertSpikeLen, cy);
      ctx.lineTo(cx + 2.8, cy);
      ctx.closePath();
      ctx.fillStyle = vGrad;
      ctx.fill();

      // Sharp vertical laser line
      ctx.beginPath();
      ctx.moveTo(cx - vertSpikeLen * 0.92, cy);
      ctx.lineTo(cx + vertSpikeLen * 0.92, cy);
      ctx.strokeStyle = `rgba(255, 255, 255, ${light})`;
      ctx.lineWidth = 1.5;
      ctx.shadowColor = '#00f0ff';
      ctx.shadowBlur = (15 * light) * renderScale;
      ctx.stroke();

      // Softer 45-degree diagonal star rays
      const diagLen = baseRadius * 1.8;
      const diagCoords = [
        [Math.SQRT1_2, Math.SQRT1_2],
        [-Math.SQRT1_2, Math.SQRT1_2],
        [-Math.SQRT1_2, -Math.SQRT1_2],
        [Math.SQRT1_2, -Math.SQRT1_2],
      ];
      ctx.beginPath();
      diagCoords.forEach(([dx, dy]) => {
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + dx * diagLen, cy + dy * diagLen);
      });
      ctx.strokeStyle = `rgba(210, 248, 255, ${0.68 * light})`;
      ctx.lineWidth = 1.2;
      ctx.shadowColor = '#38bdf8';
      ctx.shadowBlur = (10) * renderScale;
      ctx.stroke();

      // ============================================================
      // 7. PURE WHITE-HOT INCANDESCENT CORE (The central supernova)
      // Gently breathes between soft and bright
      // ============================================================
      const innerCoreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 21);
      innerCoreGrad.addColorStop(0, `rgba(255, 255, 255, ${light})`);
      innerCoreGrad.addColorStop(0.38, `rgba(255, 255, 255, ${0.98 * light})`);
      innerCoreGrad.addColorStop(0.72, `rgba(224, 247, 255, ${0.88 * light})`);
      innerCoreGrad.addColorStop(1, 'rgba(56, 189, 248, 0)');

      ctx.beginPath();
      ctx.arc(cx, cy, 21, 0, Math.PI * 2);
      ctx.fillStyle = innerCoreGrad;
      ctx.shadowColor = '#ffffff';
      ctx.shadowBlur = (25 * light) * renderScale;
      ctx.fill();

      // Diamond focal point at the absolute center
      ctx.beginPath();
      const dSize = 7.5;
      ctx.moveTo(cx, cy - dSize);
      ctx.lineTo(cx + dSize, cy);
      ctx.lineTo(cx, cy + dSize);
      ctx.lineTo(cx - dSize, cy);
      ctx.closePath();
      ctx.fillStyle = `rgba(255, 255, 255, ${light})`;
      ctx.fill();

      ctx.restore();
      ctx.restore();

      schedule();
    }

    animId = requestAnimationFrame(render);

    return () => {
      active = false; self.clearTimeout(timer);
      cancelAnimationFrame(animId);
    };
}
