import React, { useEffect, useRef, useState } from 'react';
import { renderStar } from '../animation/renderers';
import { startCanvasWorker } from '../animation/startCanvasWorker';
import { CronosState } from '../types/cronos';

interface StellarCoreProps {
  state: CronosState;
  audioLevelSource?: React.RefObject<number>;
  audioLevel?: number;
  onClick?: () => void;
  size?: number; // default 210
  className?: string;
}

export const StellarCore: React.FC<StellarCoreProps> = ({
  state,
  audioLevel = 0,
  audioLevelSource,
  onClick,
  size = 210,
  className = '',
}) => {
  const [workerFailed,setWorkerFailed]=useState(false);
  const sourceRef=useRef(audioLevelSource);sourceRef.current=audioLevelSource;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef<CronosState>(state);
  const audioLevelRef = useRef<number>(audioLevel);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    audioLevelRef.current = audioLevel;
  }, [audioLevel]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const worker = !workerFailed && startCanvasWorker(canvas, 'star', size, 1, () => ({state:stateRef.current,audio:sourceRef.current?.current??audioLevelRef.current,hidden:document.hidden||document.documentElement.dataset.cronosPanel==='true',links:true}),()=>setWorkerFailed(true));
    if(worker)return worker;
    return renderStar(canvas,size,1,window.devicePixelRatio||1,()=>({state:stateRef.current,audio:sourceRef.current?.current??audioLevelRef.current,hidden:document.hidden||document.documentElement.dataset.cronosPanel==='true',links:true}));
  }, [workerFailed]);

  return (
    <div
      className={`relative flex items-center justify-center cursor-pointer select-none pointer-events-auto ${className}`}
      style={{ width: size, height: size }}
      onClick={onClick}
      title="Núcleo Estelar (Clique para interagir com o CRONOS)"
    >
      <canvas
        key={workerFailed?'fallback':'worker'}
        ref={canvasRef}
        width={600}
        height={600}
        className="w-full h-full max-w-none overflow-visible pointer-events-auto"
      />
    </div>
  );
};
