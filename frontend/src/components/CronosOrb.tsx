import React, { useEffect, useRef, useState } from 'react';
import { renderOrb } from '../animation/renderers';
import { startCanvasWorker } from '../animation/startCanvasWorker';
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

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const worker = !workerFailed && startCanvasWorker(canvas, 'orb', size, weaveDensity, () => ({state:stateRef.current,audio:sourceRef.current?.current??audioLevelRef.current,hidden:document.hidden||document.documentElement.dataset.cronosPanel==='true',links:showCrossLinksRef.current}),()=>setWorkerFailed(true));
    if(worker)return worker;
    return renderOrb(canvas,size,weaveDensity,window.devicePixelRatio||1,()=>({state:stateRef.current,audio:sourceRef.current?.current??audioLevelRef.current,hidden:document.hidden||document.documentElement.dataset.cronosPanel==='true',links:showCrossLinksRef.current}));
  }, [weaveDensity,workerFailed]);

  return (
    <div
      className={`relative flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      onClick={onOrbClick}
    >
      {/* 3D Interwoven Fabric Hologram Canvas: All organic waves, inner aura & outer aura rendered dynamically */}
      <div className={`filament-aura ${state === 'SPEAKING' ? 'speaking' : ''}`} />
      <canvas
        key={workerFailed?'fallback':'worker'}
        ref={canvasRef}
        width={1200}
        height={1200}
        className={`w-full h-full max-w-none cursor-pointer relative z-10 filament-glow transition-all duration-500 ${
          state === 'SPEAKING' ? 'speaking' : ''
        }`}
        title="CRONOS // Núcleo Holográfico de Linhas Conectadas (Clique para testar voz)"
      />
    </div>
  );
};
