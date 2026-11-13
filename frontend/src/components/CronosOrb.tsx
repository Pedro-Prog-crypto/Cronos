import React, { useEffect, useRef, useState } from 'react';
import { renderOrb } from '../animation/renderers';
import { orbRenderRatio, startCanvasWorker } from '../animation/startCanvasWorker';
import { CronosState } from '../types/cronos';

interface CronosOrbProps {
  state: CronosState;
  audioLevelSource?: React.RefObject<number>;
  audioLevel?: number; // 0.0 to 1.0, real-time speech output volume
  onOrbClick?: () => void;
  className?: string;
  size?: number; // default 580
  weaveDensity?: number; // 1.0 default
  showCrossLinks?: boolean; // connect lines like fabric
}

export const CronosOrb: React.FC<CronosOrbProps> = ({
  state,
  audioLevel = 0,
  audioLevelSource,
  onOrbClick,
  className = '',
  size = 580,
  weaveDensity = 1.0,
  showCrossLinks = true,
}) => {
  const [workerFailed,setWorkerFailed]=useState(false);
  const [renderRevision,setRenderRevision]=useState(0);
  const sourceRef=useRef(audioLevelSource);sourceRef.current=audioLevelSource;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef<CronosState>(state);
  const audioLevelRef = useRef<number>(audioLevel);
  const showCrossLinksRef = useRef<boolean>(showCrossLinks);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    audioLevelRef.current = audioLevel;
  }, [audioLevel]);

  useEffect(() => {
    showCrossLinksRef.current = showCrossLinks;
  }, [showCrossLinks]);

  useEffect(()=>{
    let timer:number|undefined;
    const resize=()=>{window.clearTimeout(timer);timer=window.setTimeout(()=>setRenderRevision(value=>value+1),180);};
    window.addEventListener('resize',resize);
    return()=>{window.removeEventListener('resize',resize);window.clearTimeout(timer);};
  },[]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const worker = !workerFailed && startCanvasWorker(canvas, 'orb', size, weaveDensity, () => ({state:stateRef.current,audio:sourceRef.current?.current??audioLevelRef.current,hidden:document.hidden,links:showCrossLinksRef.current,fps:document.documentElement.dataset.cronosEconomy==='true'?24:60}),()=>setWorkerFailed(true));
    if(worker)return worker;
    return renderOrb(canvas,size,weaveDensity,orbRenderRatio(canvas,size),()=>({state:stateRef.current,audio:sourceRef.current?.current??audioLevelRef.current,hidden:document.hidden,links:showCrossLinksRef.current,fps:document.documentElement.dataset.cronosEconomy==='true'?24:60}));
  }, [size,weaveDensity,workerFailed,renderRevision]);

  return (
    <div
      className={`relative flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      onClick={onOrbClick}
    >
      {/* Animated contour and independent filaments; the aura supplies the blue field. */}
      <div className={`filament-aura ${state === 'SPEAKING' ? 'speaking' : ''}`} />
      <canvas
        key={`${workerFailed?'fallback':'worker'}-${renderRevision}`}
        ref={canvasRef}
        width={1200}
        height={1200}
        className={`w-full h-full max-w-none cursor-pointer relative z-10 filament-glow transition-all duration-500 ${
          state === 'SPEAKING' ? 'speaking' : ''
        }`}
        title="CRONOS // Holograma ativo (clique para testar voz)"
      />
    </div>
  );
};
