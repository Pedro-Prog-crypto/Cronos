import React, { useState, useEffect } from 'react';
import { CronosState } from '../types/cronos';
import { Radio, ShieldCheck, Cpu, Wifi } from 'lucide-react';

interface TopHudProps {
  state: CronosState;
  currentStageText?: string;
  onStateChange?: (newState: CronosState) => void;
}

export const TopHud: React.FC<TopHudProps> = ({
  state,
  currentStageText,
  onStateChange,
}) => {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString('pt-BR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const getStateBadge = () => {
    switch (state) {
      case 'SPEAKING':
        return {
          label: 'FALANDO',
          color: 'text-cyan-300 border-cyan-400/50 bg-cyan-950/40 shadow-[0_0_15px_rgba(0,229,255,0.4)]',
          dot: 'bg-cyan-400 shadow-[0_0_8px_#00e5ff] animate-pulse',
        };
      case 'LISTENING':
        return {
          label: 'OUVINDO',
          color: 'text-sky-300 border-sky-400/50 bg-sky-950/40 shadow-[0_0_15px_rgba(56,189,248,0.4)]',
          dot: 'bg-sky-400 shadow-[0_0_8px_#38bdf8] animate-ping',
        };
      default:
        return {
          label: 'EM ESPERA',
          color: 'text-blue-300/80 border-blue-500/30 bg-blue-950/30',
          dot: 'bg-blue-500 shadow-[0_0_6px_#3b82f6]',
        };
    }
  };

  const badge = getStateBadge();

  return (
    <header className="relative z-30 w-full px-6 py-4 flex items-center justify-between pointer-events-auto">
      {/* Left zone: System tags & telemetry */}
      <div className="flex items-center gap-4 text-xs font-mono text-blue-300/70">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span className="hidden sm:inline tracking-wider">
            RECONHECIDO // CRONOGRAMA // MENSAGEM OK
          </span>
          <span className="sm:hidden tracking-wider">CRONOS // OK</span>
        </div>

        <div className="hidden lg:flex items-center gap-2 text-[11px] text-blue-400/50 border-l border-blue-900/50 pl-3">
          <Cpu className="w-3.5 h-3.5 text-blue-400" />
          <span>NEURAL CORE 60 FPS</span>
        </div>
      </div>

      {/* Center zone: CRONOS Brand & State Pill */}
      <div className="flex flex-col items-center">
        <h1 className="text-xl sm:text-2xl font-bold tracking-[0.28em] font-mono text-transparent bg-clip-text bg-gradient-to-r from-blue-200 via-cyan-200 to-blue-300 drop-shadow-[0_0_15px_rgba(0,180,255,0.6)]">
          CRONOS
        </h1>

        {/* State Pill */}
        <div
          className={`mt-1 flex items-center gap-2 px-3 py-0.5 rounded-full border text-[11px] font-mono tracking-[0.2em] uppercase font-semibold transition-all duration-500 ${badge.color}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
          <span>{badge.label}</span>
          {currentStageText && state === 'SPEAKING' && (
            <>
              <span className="text-cyan-500/60">·</span>
              <span className="text-[10px] text-cyan-200/80 normal-case font-sans tracking-normal truncate max-w-[150px]">
                {currentStageText}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Right zone: Live time & interactive state switches */}
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 font-mono text-xs text-cyan-300/80 bg-[#040e25]/60 px-2.5 py-1 rounded-lg border border-blue-500/20 tabular-nums">
          <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>{timeStr}</span>
        </div>

        {/* State testing shortcuts */}
        {onStateChange && (
          <div className="hidden md:flex items-center p-0.5 rounded-lg bg-[#040f28]/80 border border-blue-500/20 text-[10px] font-mono">
            <button
              onClick={() => onStateChange('IDLE')}
              className={`px-2 py-1 rounded transition-colors cursor-pointer ${
                state === 'IDLE'
                  ? 'bg-blue-600/40 text-cyan-200 border border-cyan-500/30'
                  : 'text-blue-300/60 hover:text-blue-200'
              }`}
              title="Modo Em Espera"
            >
              ESPERA
            </button>
            <button
              onClick={() => onStateChange('LISTENING')}
              className={`px-2 py-1 rounded transition-colors cursor-pointer ${
                state === 'LISTENING'
                  ? 'bg-sky-600/40 text-sky-200 border border-sky-400/30'
                  : 'text-blue-300/60 hover:text-sky-200'
              }`}
              title="Modo Ouvindo"
            >
              ESCUTA
            </button>
            <button
              onClick={() => onStateChange('SPEAKING')}
              className={`px-2 py-1 rounded transition-colors cursor-pointer ${
                state === 'SPEAKING'
                  ? 'bg-cyan-600/40 text-cyan-100 border border-cyan-400/40'
                  : 'text-blue-300/60 hover:text-cyan-200'
              }`}
              title="Modo Falando"
            >
              FALA
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
