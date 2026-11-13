import {CronosState} from '../types/cronos';
import referenceFramesUrl from '../assets/images/hologram-reference-frames-a.png?url';
export type SceneInput={state:CronosState;audio:number;hidden:boolean;links:boolean;fps?:number};
type SceneCanvas=HTMLCanvasElement|OffscreenCanvas;
function context(canvas:SceneCanvas){return canvas.getContext('2d') as CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D|null;}

/** The reference's actual light texture is deformed continuously, never switched frame by frame. */
export function renderOrb(canvas:SceneCanvas,size:number,density:number,pixelRatio:number,input:()=>SceneInput){
 const bitmap=Math.min(900,Math.round(size*Math.min(pixelRatio,900/size)));
 canvas.width=canvas.height=bitmap;
 const gl=(canvas as HTMLCanvasElement).getContext('webgl',{alpha:true,antialias:true,premultipliedAlpha:false}) as WebGLRenderingContext|null;
 if(!gl)return renderOrbVectors(canvas,size,density,pixelRatio,input);
 const vertex=`attribute vec2 position;varying vec2 uv;void main(){uv=(position+1.0)*0.5;gl_Position=vec4(position,0.0,1.0);}`;
 const fragment=`precision highp float;
 varying vec2 uv;uniform sampler2D source;uniform float phase;uniform float energy;
 void main(){
   vec2 p=uv-vec2(.5);float angle=atan(p.y,p.x);float radius=length(p);
   float flowing=angle-phase*1.1-(.038+energy*.025)*sin(angle*2.0+phase*.91)-.018*sin(angle*3.0-phase*.62);
   float warped=radius+(.010+energy*.005)*sin(angle*2.0+phase*.88)+.005*sin(angle*3.0-phase*.55);
   vec2 sampleAt=vec2(.5)+vec2(cos(flowing),sin(flowing))*warped;
   vec3 light=texture2D(source,vec2(sampleAt.x,1.0-sampleAt.y)).rgb;
   float peak=max(max(light.r,light.g),light.b);
   float inside=step(0.0,sampleAt.x)*step(sampleAt.x,1.0)*step(0.0,sampleAt.y)*step(sampleAt.y,1.0);
   float sourceRadius=length(sampleAt-vec2(.5));
   float opacity=smoothstep(.055,.20,peak)*(1.0-smoothstep(.42,.47,radius))*(1.0-smoothstep(.43,.48,sourceRadius))*inside;
   float glimmer=1.0+.10*sin(angle*3.0-phase*1.35)+energy*.15;
   gl_FragColor=vec4(min(light*glimmer,1.0),opacity);
 }`;
 const shader=(type:number,source:string)=>{const value=gl.createShader(type);if(!value)throw new Error('Hologram shader unavailable');gl.shaderSource(value,source);gl.compileShader(value);if(!gl.getShaderParameter(value,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(value)||'Hologram shader failed');return value;};
 const program=gl.createProgram();if(!program)throw new Error('Hologram program unavailable');
 gl.attachShader(program,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);
 if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program)||'Hologram link failed');
 gl.useProgram(program);
 const quad=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,quad);
 gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
 const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
 const phaseUniform=gl.getUniformLocation(program,'phase'),energyUniform=gl.getUniformLocation(program,'energy');
 const texture=gl.createTexture();gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
 gl.uniform1i(gl.getUniformLocation(program,'source'),0);gl.viewport(0,0,bitmap,bitmap);
 let active=true,ready=false,frame=0,timer=0,last=performance.now(),motion=0,velocity=.18,energy=.06;
 void (async()=>{
  const response=await fetch(referenceFramesUrl);if(!response.ok)throw new Error(`Hologram reference ${response.status}`);
  const sheet=await createImageBitmap(await response.blob());
  try{const source=await createImageBitmap(sheet,0,0,sheet.width/3,sheet.height/2);
   try{if(!active)return;gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,1);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,source);ready=true;}
   finally{source.close();}}
  finally{sheet.close();}
 })().catch(error=>console.warn('Hologram reference unavailable.',error));
 const schedule=(delay=0)=>{if(!active)return;if(delay)timer=self.setTimeout(()=>{if(active)frame=requestAnimationFrame(draw);},delay);else frame=requestAnimationFrame(draw);};
 const draw=()=>{
  if(!active)return;const value=input(),now=performance.now();
  if(value.hidden){last=now;schedule(180);return;}
  if(now-last<1000/(value.fps||60)-1){schedule();return;}
  const dt=Math.min(.05,(now-last)/1000);last=now;
  const level=Math.max(0,Math.min(1,value.audio));
  const targetVelocity=value.state==='SPEAKING'?.62+level*.18:value.state==='LISTENING'?.36+level*.10:.18;
  const targetEnergy=value.state==='SPEAKING'?.62+level*.32:value.state==='LISTENING'?.34+level*.18:.06;
  velocity+=(targetVelocity-velocity)*Math.min(1,dt*3.4);energy+=(targetEnergy-energy)*Math.min(1,dt*4.2);
  motion+=dt*velocity;
  if(ready){gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.uniform1f(phaseUniform,motion);gl.uniform1f(energyUniform,energy);gl.drawArrays(gl.TRIANGLE_STRIP,0,4);}
  schedule();
 };
 frame=requestAnimationFrame(draw);
 return ()=>{active=false;self.clearTimeout(timer);cancelAnimationFrame(frame);gl.deleteTexture(texture);gl.deleteBuffer(quad);gl.deleteProgram(program);};
}

/** Vector fallback for devices where the graphic driver does not expose WebGL. */
function renderOrbVectors(canvas:SceneCanvas,size:number,_density:number,pixelRatio:number,input:()=>SceneInput){
 const ctx=context(canvas);if(!ctx)return;
 const logical=600,ratio=Math.min(pixelRatio,900/size),bitmap=Math.min(900,Math.round(size*ratio)),scale=bitmap/logical;
 canvas.width=canvas.height=bitmap;ctx.setTransform(scale,0,0,scale,0,0);
 const count=7,steps=240,tau=Math.PI*2;
 const circle=Array.from({length:steps+1},(_,i)=>{const u=i*tau/steps;return {u,c:Math.cos(u),s:Math.sin(u)};});
 const paths=Array.from({length:count},()=>new Float32Array((steps+1)*2));
 let active=true,frame=0,timer=0,last=performance.now(),phase=0,velocity=.18,energy=.06;
 const schedule=(delay=0)=>{if(!active)return;if(delay)timer=self.setTimeout(()=>{if(active)frame=requestAnimationFrame(draw);},delay);else frame=requestAnimationFrame(draw);};
 const trace=(path:Float32Array)=>{ctx.beginPath();ctx.moveTo(path[0],path[1]);for(let j=2;j<path.length;j+=2)ctx.lineTo(path[j],path[j+1]);ctx.closePath();};
 const highlight=(path:Float32Array,angle:number,halfWidth:number)=>{
  const center=Math.round((((angle%tau)+tau)%tau)/tau*steps);
  const half=Math.round(halfWidth/tau*steps);
  ctx.beginPath();
  for(let offset=-half;offset<=half;offset++){
   const index=(center+offset+steps)%steps;
   if(offset===-half)ctx.moveTo(path[index*2],path[index*2+1]);
   else ctx.lineTo(path[index*2],path[index*2+1]);
  }
 };
 const draw=()=>{
  if(!active)return;
  const value=input(),now=performance.now();
  if(value.hidden){last=now;schedule(180);return;}
  const fps=value.fps||60;
  if(now-last<1000/fps-1){schedule();return;}
  const dt=Math.min(.05,(now-last)/1000);last=now;
  const level=Math.max(0,Math.min(1,value.audio));
  const targetVelocity=value.state==='SPEAKING'?.57+level*.16:value.state==='LISTENING'?.34+level*.09:.18;
  const targetEnergy=value.state==='SPEAKING'?.58+level*.34:value.state==='LISTENING'?.32+level*.18:.06;
  velocity+=(targetVelocity-velocity)*Math.min(1,dt*3.4);
  energy+=(targetEnergy-energy)*Math.min(1,dt*4.2);
  phase+=dt*velocity;
  ctx.clearRect(0,0,logical,logical);
  const baseRadius=194+Math.sin(phase*.56)*1.8;
  for(let strand=0;strand<count;strand++){
   const path=paths[strand],offset=strand*tau/count;
   for(let i=0;i<=steps;i++){
    const {u,c,s}=circle[i];
    // Low spatial frequencies keep each strand smooth; time enters only as a
    // continuous phase, so there are no image cuts or repeated sprite cycles.
    const radial=baseRadius
     +Math.sin(2*u+offset+phase*.91)*(16+energy*6)
     +Math.sin(3*u-offset*.72-phase*.62)*(8+energy*4)
     +Math.sin(u+offset*.45+phase*.43)*(5+energy*3)
     +energy*5*Math.sin(2*u-phase*1.16)*Math.cos(u+offset);
    path[i*2]=300+c*radial*(1+Math.sin(offset+phase*.28)*.006);
    path[i*2+1]=300+s*radial*(1+Math.cos(offset-phase*.23)*.006);
   }
  }
  ctx.save();ctx.globalCompositeOperation='screen';ctx.lineJoin='round';ctx.lineCap='round';
  for(let strand=0;strand<count;strand++){
   const path=paths[strand];trace(path);
   ctx.shadowColor='#0089ff';ctx.shadowBlur=10+energy*4;
   ctx.strokeStyle=strand%2?'rgba(0,108,230,.59)':'rgba(0,161,255,.55)';
   ctx.lineWidth=4.2;ctx.stroke();
   ctx.shadowBlur=0;
   ctx.strokeStyle=strand%3===0?'rgba(148,241,255,.91)':'rgba(28,197,255,.82)';
   ctx.lineWidth=1.55;ctx.stroke();
  }
  for(let strand=0;strand<count;strand++){
   const path=paths[strand];
   const angle=phase*(1.1+strand*.065)+strand*2.38;
   const strength=strand%3===0?.94:.58;
   highlight(path,angle,.38+energy*.06);
   ctx.shadowColor='#13d9ff';ctx.shadowBlur=15+energy*8;
   ctx.strokeStyle=`rgba(6,191,255,${strength})`;ctx.lineWidth=4.4;ctx.stroke();
   ctx.shadowBlur=2;
   ctx.strokeStyle=`rgba(211,250,255,${strength*.92})`;ctx.lineWidth=1.6;ctx.stroke();
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
