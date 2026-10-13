import {CronosState} from '../types/cronos';
export type SceneInput={state:CronosState;audio:number;hidden:boolean;links:boolean};
type SceneCanvas=HTMLCanvasElement|OffscreenCanvas;
function context(canvas:SceneCanvas){return canvas.getContext('2d') as CanvasRenderingContext2D|OffscreenCanvasRenderingContext2D|null;}
function buffer():SceneCanvas{return typeof OffscreenCanvas!=='undefined'?new OffscreenCanvas(1,1):document.createElement('canvas');}
interface StrandConfig {
  family: 'warp' | 'weft' | 'core';
  helixWinding: number;
  speed: number;
  amp: number;
  harmonics: [number, number, number];
  weights: [number, number, number];
  tubeRadiusOffset: number;
  phase: number;
  baseAlpha: number;
  strokeWidth: number;
  colorRGB: [number, number, number];
}

interface SparkNode {
  strandIndex: number;
  u: number;
  speed: number;
  size: number;
  color: string;
}

export function renderOrb(canvas:SceneCanvas,size:number,weaveDensity:number,pixelRatio:number,input:()=>SceneInput){
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
    const width = 1200, height = 1200;
    // Match bitmap to displayed size; preserve original geometry in logical coordinates.
    const renderScale = Math.min(1200, Math.ceil(size * Math.min(pixelRatio, 1.25))) / 1200;
    canvas.width = Math.ceil(width * renderScale);canvas.height = Math.ceil(height * renderScale);
    ctx.setTransform(renderScale,0,0,renderScale,0,0);
    const glowCanvas = buffer();glowCanvas.width=Math.ceil(canvas.width/2);glowCanvas.height=Math.ceil(canvas.height/2);
    const glowCtx=context(glowCanvas)!;glowCtx.setTransform(renderScale/2,0,0,renderScale/2,0,0);
    const bloomCanvas = buffer();bloomCanvas.width=glowCanvas.width;bloomCanvas.height=glowCanvas.height;
    const bloomCtx=context(bloomCanvas)!;
    const centerX = width / 2;
    const centerY = height / 2;

    const IDLE_MAJOR_RADIUS = 300;
    const SPEAKING_MAJOR_RADIUS_BOOST = 65;
    const LISTENING_MAJOR_RADIUS_BOOST = 22;

    const BASE_TUBE_RADIUS = 32;

    let time = 0;
    let currentMajorRadius = IDLE_MAJOR_RADIUS;
    let targetMajorRadius = IDLE_MAJOR_RADIUS;

    let currentTubeRadius = BASE_TUBE_RADIUS;
    let targetTubeRadius = BASE_TUBE_RADIUS;

    let currentSpeed = 0.007;
    let targetSpeed = 0.007;

    let currentTurbulence = 0.15;
    let targetTurbulence = 0.15;

    let currentGlow = 1.0;
    let targetGlow = 1.0;

    // Perspective projection
    const pitch = 0.28;
    const yaw = 0.12;
    const cosPitch = Math.cos(pitch);
    const sinPitch = Math.sin(pitch);
    const cosYaw = Math.cos(yaw);
    const sinYaw = Math.sin(yaw);

    // Build the interwoven strands (tecido 3D de fios conectados)
    const strands: StrandConfig[] = [];

    // Family 1: Clockwise spiral warp threads (8 strands)
    for (let i = 0; i < 8; i++) {
      const frac = i / 8;
      strands.push({
        family: 'warp',
        helixWinding: 3.0,
        speed: 0.012 + (i % 3) * 0.002,
        amp: 12 + (i % 4) * 2.5,
        harmonics: [3, 5, 8],
        weights: [0.55, 0.3, 0.15],
        tubeRadiusOffset: (frac - 0.5) * 16,
        phase: frac * Math.PI * 2,
        baseAlpha: 0.75 + (i % 2) * 0.2,
        strokeWidth: 0.95 + (i % 3) * 0.2,
        colorRGB: i % 2 === 0 ? [0, 225, 255] : [24, 140, 255],
      });
    }

    // Family 2: Counter-clockwise spiral weft threads (8 strands, crossing over Family 1)
    for (let i = 0; i < 8; i++) {
      const frac = i / 8;
      strands.push({
        family: 'weft',
        helixWinding: -3.0,
        speed: -0.011 - (i % 3) * 0.002,
        amp: 13 + (i % 3) * 2.5,
        harmonics: [4, 6, 2],
        weights: [0.5, 0.35, 0.15],
        tubeRadiusOffset: (frac - 0.5) * 18,
        phase: (frac + 0.33) * Math.PI * 2,
        baseAlpha: 0.7 + (i % 2) * 0.25,
        strokeWidth: 1.0 + (i % 2) * 0.25,
        colorRGB: i % 3 === 0 ? [56, 189, 248] : [0, 240, 255],
      });
    }

    // Family 3: Equatorial high-speed silk core threads (4 strands)
    for (let i = 0; i < 4; i++) {
      const frac = i / 4;
      strands.push({
        family: 'core',
        helixWinding: 1.0,
        speed: 0.009,
        amp: 9,
        harmonics: [2, 4, 6],
        weights: [0.6, 0.25, 0.15],
        tubeRadiusOffset: (frac - 0.5) * 8,
        phase: frac * Math.PI * 2,
        baseAlpha: 0.85,
        strokeWidth: 1.25,
        colorRGB: [220, 250, 255],
      });
    }

    // Photonic sparks
    const sparks: SparkNode[] = [];
    for (let i = 0; i < 16; i++) {
      sparks.push({
        strandIndex: (i * 2) % strands.length,
        u: (i / 16) * Math.PI * 2,
        speed: 0.004 + (i % 4) * 0.002,
        size: 1.6 + (i % 3) * 0.6,
        color: i % 3 === 0 ? '#ffffff' : '#00f0ff',
      });
    }

    function get3DPoint(
      strand: StrandConfig,
      u: number,
      t: number,
      majorR: number,
      tubeR: number,
      turbulence: number,
      audioMod: number
    ) {
      const windingAngle =
        strand.helixWinding * u +
        t * strand.speed * 45 +
        strand.phase;

      const h = strand.harmonics;
      const w = strand.weights;
      const wave =
        Math.sin(u * h[0] + t * 4.2 + strand.phase) * w[0] +
        Math.cos(u * h[1] - t * 3.1 + strand.phase * 0.8) * w[1] +
        Math.sin(u * h[2] + t * 5.5) * w[2];

      let acousticRipple = 0;
      if (turbulence > 0.3) {
        const flutter =
          Math.sin(u * 12 + t * 14) * 3.5 +
          Math.cos(u * 20 - t * 18) * 2.2;
        acousticRipple = flutter * (turbulence - 0.2);

        if (audioMod > 0.05) {
          acousticRipple +=
            Math.sin(u * 16 + t * 24) * (audioMod * 12) +
            Math.cos(u * 8 - t * 16) * (audioMod * 8);
        }
      }

      const localTubeR = (tubeR + strand.tubeRadiusOffset) * (1 + wave * 0.18);
      const rOffset = Math.cos(windingAngle) * localTubeR + wave * strand.amp + acousticRipple;
      const zOffset = Math.sin(windingAngle) * localTubeR;

      const currentR = majorR + rOffset;
      const worldX = currentR * Math.cos(u);
      const worldY = currentR * Math.sin(u);
      const worldZ = zOffset;

      const y1 = worldY * cosPitch - worldZ * sinPitch;
      const z1 = worldY * sinPitch + worldZ * cosPitch;

      const x2 = worldX * cosYaw + z1 * sinYaw;
      const z2 = -worldX * sinYaw + z1 * cosYaw;

      const fov = 1100;
      const perspective = fov / (fov + z2);

      const projX = centerX + x2 * perspective;
      const projY = centerY + y1 * perspective;

      return {
        x: projX,
        y: projY,
        z: z2,
        perspective,
        distFromCenter: Math.hypot(projX - centerX, projY - centerY),
      };
    }

    function render() {
      if (!ctx || !active) return;
      if (input().hidden) {
        previousFrame = performance.now(); schedule(150); return;
      }
      const now = performance.now();
      if (now - previousFrame < 1000 / 30 - 1) { schedule(); return; }
      const frameDelta = Math.min(3, Math.max(.5, (now - previousFrame) / (1000 / 60)));
      previousFrame = now;
      ctx.clearRect(0, 0, width, height);

      const currentState = input().state;
      const currentAudio = input().audio;

      if (currentState === 'SPEAKING') {
        targetMajorRadius =
          IDLE_MAJOR_RADIUS +
          SPEAKING_MAJOR_RADIUS_BOOST +
          currentAudio * 16;
        targetTubeRadius = BASE_TUBE_RADIUS * (1.35 + currentAudio * 0.25);
        targetSpeed = 0.016 + currentAudio * 0.008;
        targetTurbulence = 1.35 + currentAudio * 0.9;
        targetGlow = 1.8 + currentAudio * 0.6;
      } else if (currentState === 'LISTENING') {
        targetMajorRadius = IDLE_MAJOR_RADIUS + LISTENING_MAJOR_RADIUS_BOOST;
        targetTubeRadius = BASE_TUBE_RADIUS * 1.15;
        targetSpeed = 0.011;
        targetTurbulence = 0.55;
        targetGlow = 1.3;
      } else {
        targetMajorRadius = IDLE_MAJOR_RADIUS;
        targetTubeRadius = BASE_TUBE_RADIUS;
        targetSpeed = 0.007;
        targetTurbulence = 0.15;
        targetGlow = 1.0;
      }

      currentMajorRadius += (targetMajorRadius - currentMajorRadius) * 0.05;
      currentTubeRadius += (targetTubeRadius - currentTubeRadius) * 0.05;
      currentSpeed += (targetSpeed - currentSpeed) * 0.05;
      currentTurbulence += (targetTurbulence - currentTurbulence) * 0.05;
      currentGlow += (targetGlow - currentGlow) * 0.05;

      let dynamicMajorR = currentMajorRadius;
      if (currentState === 'SPEAKING') {
        const breathing =
          Math.sin(time * 3.0) * 8.0 +
          Math.cos(time * 1.5) * 4.5 +
          currentAudio * 6;
        dynamicMajorR += breathing;
      } else {
        dynamicMajorR += Math.sin(time * 1.8) * 2.8;
      }

      time += currentSpeed * frameDelta;

      // Calculate all 3D points along the ring (120 steps)
      const steps = 120;
      const strandPoints: Array<
        Array<{ x: number; y: number; z: number; perspective: number; distFromCenter: number }>
      > = [];

      for (let sIdx = 0; sIdx < strands.length; sIdx++) {
        const strand = strands[sIdx];
        const pts: Array<{ x: number; y: number; z: number; perspective: number; distFromCenter: number }> = [];

        for (let i = 0; i <= steps; i++) {
          const u = (i / steps) * Math.PI * 2;
          const pt = get3DPoint(
            strand,
            u,
            time,
            dynamicMajorR,
            currentTubeRadius,
            currentTurbulence,
            currentAudio
          );
          pts.push(pt);
        }
        strandPoints.push(pts);
      }

      // Compute dynamic inner and outer envelopes from the live undulating strands
      // This ensures the light inside and outside follows the exact organic wave motion!
      const innerEnvelope: Array<{ x: number; y: number }> = [];
      const outerEnvelope: Array<{ x: number; y: number }> = [];

      for (let i = 0; i <= steps; i++) {
        let minDist = Infinity;
        let maxDist = -Infinity;
        let innerPt = { x: centerX, y: centerY };
        let outerPt = { x: centerX, y: centerY };

        for (let s = 0; s < strands.length; s++) {
          const p = strandPoints[s][i];
          if (!p) continue;
          if (p.distFromCenter < minDist) {
            minDist = p.distFromCenter;
            innerPt = { x: p.x, y: p.y };
          }
          if (p.distFromCenter > maxDist) {
            maxDist = p.distFromCenter;
            outerPt = { x: p.x, y: p.y };
          }
        }
        innerEnvelope.push(innerPt);
        outerEnvelope.push(outerPt);
      }

      ctx.save();

      // 1. DYNAMIC FLUID INNER VOID & LIGHT
      // Rather than a static circle, this follows the undulating inner boundary!
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const pt = innerEnvelope[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.closePath();
      // Soft dark interior that conforms to the wavy inner envelope
      const innerGradient = ctx.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        dynamicMajorR * 0.75
      );
      innerGradient.addColorStop(0, 'rgba(0, 0, 0, 0.98)');
      innerGradient.addColorStop(0.7, 'rgba(1, 4, 14, 0.92)');
      innerGradient.addColorStop(1, 'rgba(3, 12, 38, 0.35)');
      ctx.fillStyle = innerGradient;
      ctx.fill();

      // 2. ORGANIC INNER AURA (Acompanha o mexido interior do holograma)
      ctx.globalCompositeOperation = 'screen';
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const pt = innerEnvelope[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.closePath();
      ctx.strokeStyle =
        currentState === 'SPEAKING'
          ? 'rgba(0, 220, 255, 0.40)'
          : 'rgba(20, 120, 255, 0.25)';
      ctx.lineWidth = currentState === 'SPEAKING' ? 3.5 : 2.0;
      ctx.shadowBlur = (18 * currentGlow) * renderScale;
      ctx.shadowColor = '#00d0ff';
      ctx.stroke();

      // 3. ORGANIC OUTER AURA (Acompanha o mexido exterior do holograma)
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const pt = outerEnvelope[i];
        if (i === 0) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.closePath();
      ctx.strokeStyle =
        currentState === 'SPEAKING'
          ? 'rgba(0, 180, 255, 0.28)'
          : 'rgba(10, 80, 220, 0.16)';
      ctx.lineWidth = currentState === 'SPEAKING' ? 4.0 : 2.5;
      ctx.shadowBlur = (24 * currentGlow) * renderScale;
      ctx.shadowColor = '#0077ff';
      ctx.stroke();

      // 4. DRAW WEFT CONNECTORS (Lattice Bridges / Tecido)
      if (input().links) {
        const linkStep = Math.max(6, Math.round(10 / weaveDensity));
        ctx.beginPath();
        ctx.lineWidth = 0.55;

        for (let i = 0; i < steps; i += linkStep) {
          for (let s = 0; s < 8; s += 2) {
            const p1 = strandPoints[s][i];
            const p2 = strandPoints[s + 8][i];

            if (p1 && p2) {
              const avgZ = (p1.z + p2.z) * 0.5;
              const dx = p1.x - p2.x;
              const dy = p1.y - p2.y;
              const distSq = dx * dx + dy * dy;

              if (distSq < 4800) {
                const alpha =
                  avgZ > 0
                    ? Math.min(0.5, 0.22 + (avgZ / 40) * 0.28)
                    : Math.max(0.08, 0.18 + (avgZ / 40) * 0.12);

                ctx.strokeStyle =
                  currentState === 'SPEAKING'
                    ? `rgba(0, 240, 255, ${alpha * 1.3})`
                    : `rgba(28, 140, 255, ${alpha})`;
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
              }
            }
          }
        }
        ctx.stroke();
      }

      // 5. RENDER ALL INTERWOVEN STRANDS (Dual-Pass Bloom)
      // Pass A: Soft luminous blurred glow hugging each undulating strand
      glowCtx.clearRect(0,0,width,height);
      for (let sIdx = 0; sIdx < strands.length; sIdx++) {
        const strand = strands[sIdx];
        const pts = strandPoints[sIdx];
        if (!pts) continue;

        glowCtx.beginPath();
        for (let i = 0; i <= steps; i++) {
          const pt = pts[i];
          if (i === 0) glowCtx.moveTo(pt.x, pt.y);
          else glowCtx.lineTo(pt.x, pt.y);
        }
        glowCtx.closePath();

        const [r, g, b] = strand.colorRGB;
        glowCtx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${strand.baseAlpha * 0.35})`;
        glowCtx.lineWidth = strand.strokeWidth * 2.8;
        glowCtx.shadowBlur = 0;
        glowCtx.shadowColor = sIdx % 2 === 0 ? '#00e5ff' : '#0077ff';
        glowCtx.stroke();
      }

      bloomCtx.clearRect(0,0,bloomCanvas.width,bloomCanvas.height);
      bloomCtx.filter=`blur(${2.5*renderScale}px)`;bloomCtx.drawImage(glowCanvas,0,0);
      ctx.save();ctx.shadowBlur=0;ctx.drawImage(bloomCanvas,0,0,width,height);ctx.restore();

      // Pass B: Sharp crisp core beam of each strand
      for (let sIdx = 0; sIdx < strands.length; sIdx++) {
        const strand = strands[sIdx];
        const pts = strandPoints[sIdx];
        if (!pts) continue;

        ctx.beginPath();
        for (let i = 0; i <= steps; i++) {
          const pt = pts[i];
          if (i === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        }
        ctx.closePath();

        const [r, g, b] = strand.colorRGB;
        let alpha = strand.baseAlpha;
        let strokeW = strand.strokeWidth;
        let glowBlur = 8 * currentGlow;

        if (currentState === 'SPEAKING') {
          alpha = Math.min(1.0, alpha * 1.35);
          strokeW = strokeW * 1.2;
          glowBlur = 18 * currentGlow;
          ctx.strokeStyle = `rgba(${Math.min(255, r + 50)}, ${Math.min(255, g + 70)}, 255, ${alpha})`;
          ctx.shadowColor = sIdx % 2 === 0 ? '#00f5ff' : '#1d8cf8';
        } else if (currentState === 'LISTENING') {
          alpha = Math.min(0.95, alpha * 1.15);
          glowBlur = 12 * currentGlow;
          ctx.strokeStyle = `rgba(${r + 20}, ${g + 35}, 255, ${alpha})`;
          ctx.shadowColor = '#38bdf8';
        } else {
          ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.9})`;
          ctx.shadowColor = strand.baseAlpha > 0.75 ? '#00e5ff' : '#0066ff';
        }

        ctx.lineWidth = strokeW;
        ctx.shadowBlur = 0;
        ctx.stroke();
      }

      // 6. PHOTONIC SPARKS GLIDING ALONG TRACKS
      sparks.forEach((spark) => {
        spark.u += spark.speed * (currentSpeed / 0.007);
        if (spark.u > Math.PI * 2) spark.u -= Math.PI * 2;

        const strand = strands[spark.strandIndex];
        const pt = get3DPoint(
          strand,
          spark.u,
          time,
          dynamicMajorR,
          currentTubeRadius,
          currentTurbulence,
          currentAudio
        );

        const pulseScale =
          (Math.sin(time * 4.0 + spark.u * 3) * 0.3 + 0.8) *
          (currentState === 'SPEAKING' ? 1.5 : 1.0);
        const nodeRadius = spark.size * pulseScale;

        const depthAlpha = pt.z > 0 ? 0.95 : 0.45;

        ctx.beginPath();
        ctx.arc(pt.x, pt.y, nodeRadius, 0, Math.PI * 2);

        if (currentState === 'SPEAKING') {
          ctx.fillStyle = `rgba(240, 255, 255, ${depthAlpha})`;
          ctx.shadowBlur = (22) * renderScale;
          ctx.shadowColor = '#00f0ff';
        } else {
          ctx.fillStyle = `rgba(186, 230, 253, ${depthAlpha * 0.85})`;
          ctx.shadowBlur = (12) * renderScale;
          ctx.shadowColor = '#38bdf8';
        }
        ctx.fill();
      });

      ctx.restore();
      schedule();
    }

    animId = requestAnimationFrame(render);

    return () => {
      active = false; self.clearTimeout(timer);
      cancelAnimationFrame(animId);
    };
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
      if (input().hidden) {
        previousFrame = performance.now(); schedule(150); return;
      }
      const now = performance.now();
      if (now - previousFrame < 1000 / 30 - 1) { schedule(); return; }
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
