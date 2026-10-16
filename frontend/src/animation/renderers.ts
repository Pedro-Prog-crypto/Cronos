import {CronosState} from '../types/cronos';
export type SceneInput={state:CronosState;audio:number;hidden:boolean;links:boolean;fps?:number};
type SceneCanvas=HTMLCanvasElement|OffscreenCanvas;
function context(canvas:SceneCanvas){return canvas.getContext('2d') as CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D|null;}
function buffer():SceneCanvas{return typeof OffscreenCanvas!=='undefined'?new OffscreenCanvas(1,1):document.createElement('canvas');}
export function renderOrb(canvas:SceneCanvas,size:number,_density:number,pixelRatio:number,input:()=>SceneInput){
 const ctx=context(canvas);if(!ctx)return;
 const logical=600,ratio=Math.min(pixelRatio,1.25),scale=Math.ceil(size*ratio)/logical;
 canvas.width=canvas.height=Math.ceil(size*ratio);ctx.setTransform(scale,0,0,scale,0,0);
 const glow=buffer();glow.width=glow.height=Math.ceil(canvas.width/2);const light=context(glow)!;
 light.setTransform(scale/2,0,0,scale/2,0,0);
 // The reference is a breathing ring of free filaments, rather than a solid torus.
 // Cache the angular basis; bounded geometry and half-resolution bloom in the worker.
 const count=14,steps=104;
 const basis=Array.from({length:steps+1},(_,i)=>{const u=i/steps*Math.PI*2;return {u,c:Math.cos(u),s:Math.sin(u)};});
 const points=Array.from({length:count},()=>new Float32Array((steps+1)*2));
 let active=true,frame=0,timer=0,last=performance.now(),time=0,energy=0;
 const schedule=(delay=0)=>{if(!active)return;if(delay)timer=self.setTimeout(()=>{if(active)frame=requestAnimationFrame(draw);},delay);else frame=requestAnimationFrame(draw);};
 const trace=(target:CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D,p:Float32Array)=>{target.beginPath();target.moveTo(p[0],p[1]);for(let j=2;j<p.length;j+=2)target.lineTo(p[j],p[j+1]);target.closePath();};
 const draw=()=>{
  if(!active)return;const value=input(),now=performance.now();
  if(value.hidden){last=now;schedule(180);return;}
  if(now-last<1000/(value.fps||30)-1){schedule();return;}
  const dt=Math.min(.06,(now-last)/1000);last=now;time+=dt;
  const target=value.state==='SPEAKING'?.6+Math.min(1,value.audio)*.7:value.state==='LISTENING'?.25:.08;
  energy+=(target-energy)*Math.min(1,dt*5);
  ctx.clearRect(0,0,logical,logical);light.clearRect(0,0,logical,logical);
  const radius=184+Math.sin(time*.85)*3+energy*8;
  for(let k=0;k<count;k++){
   const phase=k*Math.PI*2/count,p=points[k],rotation=time*(k%2?.2:-.16);
   for(let i=0;i<=steps;i++){
    const {u,c,s}=basis[i],wave=Math.sin(u*3+phase+rotation)*(.55+energy*.22)+Math.sin(u*5-phase*.7-time*.45)*.27;
    const r=radius+wave*(18+energy*15)+Math.cos(u*2+phase-time*.32)*8;
    const z=Math.sin(u*3+phase+rotation)*12;
    p[i*2]=300+c*r+z*.12;p[i*2+1]=300+s*r*.96-z*.18;
   }
   trace(light,p);light.strokeStyle=k%3?'rgba(17,98,255,.48)':'rgba(0,210,255,.55)';light.lineWidth=6+energy*2;light.stroke();
  }
  const voidLight=ctx.createRadialGradient(300,300,0,300,300,radius-6);voidLight.addColorStop(0,'rgba(0,2,10,.96)');voidLight.addColorStop(.85,'rgba(1,5,20,.8)');voidLight.addColorStop(1,'rgba(0,8,30,0)');ctx.fillStyle=voidLight;ctx.beginPath();ctx.arc(300,300,radius-6,0,Math.PI*2);ctx.fill();
  ctx.save();ctx.globalCompositeOperation='screen';
  const aura=ctx.createRadialGradient(300,300,radius-35,300,300,radius+65);
  aura.addColorStop(0,'rgba(0,40,130,0)');aura.addColorStop(.42,'rgba(0,90,255,.13)');aura.addColorStop(.7,'rgba(0,105,255,.035)');aura.addColorStop(1,'rgba(0,70,255,0)');
  ctx.fillStyle=aura;ctx.fillRect(50,50,500,500);
  ctx.drawImage(glow,0,0,logical,logical);
  for(let k=0;k<count;k++){
   trace(ctx,points[k]);ctx.strokeStyle=k%4===0?'rgba(133,234,255,.92)':k%2?'rgba(15,118,255,.9)':'rgba(0,203,255,.78)';ctx.lineWidth=(k%4===0?1:.72)+energy*.18;ctx.stroke();
  }
  // Small highlights run along the same filaments without a second particle scene.
  for(let k=0;k<6;k++){
   const p=points[k*2],j=Math.floor(((time*(.035+k*.003)+k/6)%1)*steps)*2;
   const halo=ctx.createRadialGradient(p[j],p[j+1],0,p[j],p[j+1],5);halo.addColorStop(0,'#c7faff');halo.addColorStop(.25,'#13d9ff');halo.addColorStop(1,'#008fff00');ctx.fillStyle=halo;ctx.beginPath();ctx.arc(p[j],p[j+1],5,0,Math.PI*2);ctx.fill();
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
