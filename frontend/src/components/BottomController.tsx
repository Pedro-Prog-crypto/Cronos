import React from 'react';
import { CronosState } from '../types/cronos';
import { Play, Pause, RotateCcw, Volume2, VolumeX, Mic } from 'lucide-react';

interface BottomControllerProps {
  state: CronosState;
  onMicClick: () => void;
  onPlayBriefing?: () => void;
  isPlayingBriefing?: boolean;
  onResetBriefing?: () => void;
  isAudioVoiceEnabled?: boolean;
  onToggleAudioVoice?: () => void;
}

export const BottomController: React.FC<BottomControllerProps> = ({
  state,
  onMicClick,
  onPlayBriefing,
  isPlayingBriefing = false,
  onResetBriefing,
  isAudioVoiceEnabled = true,
  onToggleAudioVoice,
}) => {
  const getStatusText = () => {
    switch (state) {
      case 'SPEAKING':
        return 'Speaking / Voice Stream Active';
      case 'LISTENING':
        return 'Listening / Audio Stream Connected';
      default:
        return 'Awaiting Audio Input';
    }
  };

  return (
    <footer className="relative z-30 w-full pb-6 pt-2 flex flex-col items-center justify-center pointer-events-auto">
      {/* Discrete Live Audio Mode Status Label */}
      <div
        className={`mb-3 flex items-center space-x-2 text-[10px] tracking-[0.22em] font-medium uppercase font-mono transition-colors duration-500 ${
          state === 'SPEAKING'
            ? 'text-cyan-300/90'
            : state === 'LISTENING'
            ? 'text-sky-300/90'
            : 'text-blue-300/60'
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full transition-all duration-500 ${
            state === 'SPEAKING'
              ? 'bg-cyan-400 shadow-[0_0_10px_#00e5ff] animate-pulse'
              : state === 'LISTENING'
              ? 'bg-sky-400 shadow-[0_0_8px_#38bdf8] animate-ping'
              : 'bg-blue-500 shadow-[0_0_6px_#3b82f6]'
          }`}
        />
        <span>{getStatusText()}</span>
      </div>

      {/* Main Interactive Mic Orb & Quick Action cluster */}
      <div className="flex items-center gap-6">
        {/* Secondary Action: Reset */}
        {onResetBriefing && (
          <button
            onClick={onResetBriefing}
            className="p-2 rounded-full bg-[#040e24]/80 border border-blue-500/25 text-blue-300/70 hover:text-cyan-200 hover:border-cyan-400/50 hover:bg-[#06183d] transition-all cursor-pointer shadow-md group"
            title="Reiniciar briefing desde o início"
          >
            <RotateCcw className="w-3.5 h-3.5 group-hover:rotate-[-45deg] transition-transform" />
          </button>
        )}

        {/* Central Stitch glowing audio controller */}
        <div
          aria-label="Alternar entrada de voz do CRONOS"
          role="button"
          tabIndex={0}
          onClick={onMicClick}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onMicClick();
            }
          }}
          className="relative flex flex-col items-center justify-center group cursor-pointer"
        >
          {/* Speaking Waveform Equalizer Indicators */}
          {state === 'SPEAKING' && (
            <div className="absolute -top-5 flex items-center justify-center space-x-1 pointer-events-none">
              <span
                className="w-[2px] bg-cyan-400/90 rounded-full sound-bar"
                style={{ animationDelay: '0.08s' }}
              />
              <span
                className="w-[2px] bg-sky-300 rounded-full sound-bar"
                style={{ animationDelay: '0.32s' }}
              />
              <span
                className="w-[2px] bg-blue-400 rounded-full sound-bar"
                style={{ animationDelay: '0.18s' }}
              />
              <span
                className="w-[2px] bg-cyan-300 rounded-full sound-bar"
                style={{ animationDelay: '0.44s' }}
              />
              <span
                className="w-[2px] bg-sky-400/90 rounded-full sound-bar"
                style={{ animationDelay: '0.14s' }}
              />
            </div>
          )}

          {/* Outer soft halo with responsive hover/active glow */}
          <div
            className={`absolute transition-all duration-500 ${
              state === 'SPEAKING'
                ? '-inset-3 bg-cyan-500/40 rounded-full blur-lg opacity-90 scale-125'
                : state === 'LISTENING'
                ? '-inset-3 bg-sky-500/35 rounded-full blur-md opacity-80 scale-115'
                : '-inset-2 bg-blue-600/25 rounded-full blur-md opacity-40 group-hover:opacity-85 group-hover:scale-125'
            }`}
          />

          {/* Subtle pulsing outer ring (idle state) */}
          {state === 'IDLE' && (
            <div className="absolute w-8 h-8 rounded-full border border-blue-500/35 animate-dock-pulse pointer-events-none group-hover:border-blue-400/60 transition-colors" />
          )}

          {/* Core minimal glowing dot with interactive scaling */}
          <div
            className={`relative w-6 h-6 rounded-full flex items-center justify-center transition-all duration-500 ${
              state === 'SPEAKING'
                ? 'bg-[#031936] border border-cyan-400 shadow-[0_0_24px_rgba(0,229,255,1)]'
                : state === 'LISTENING'
                ? 'bg-[#042045] border border-sky-400 shadow-[0_0_18px_rgba(56,189,248,0.9)]'
                : 'bg-[#05112a] border border-blue-500/50 shadow-[0_0_12px_rgba(37,99,235,0.7)] group-hover:shadow-[0_0_20px_rgba(56,189,248,1)] group-hover:border-sky-400/80'
            }`}
          >
            <span
              className={`rounded-full transition-colors ${
                state === 'SPEAKING'
                  ? 'w-2 h-2 bg-cyan-300 shadow-[0_0_10px_#00e5ff] animate-pulse'
                  : state === 'LISTENING'
                  ? 'w-2 h-2 bg-sky-300 shadow-[0_0_8px_#38bdf8]'
                  : 'w-1.5 h-1.5 bg-blue-400 shadow-[0_0_6px_#3b82f6] group-hover:bg-cyan-300'
              }`}
            />
          </div>
        </div>

        {/* Primary Action: Play/Pause Briefing */}
        {onPlayBriefing && (
          <button
            onClick={onPlayBriefing}
            className={`px-3.5 py-1.5 rounded-full border text-xs font-mono tracking-wider flex items-center gap-1.5 transition-all duration-300 cursor-pointer shadow-lg ${
              isPlayingBriefing
                ? 'bg-cyan-950/70 border-cyan-400/70 text-cyan-200 shadow-[0_0_15px_rgba(0,229,255,0.25)]'
                : 'bg-[#041029]/80 border-blue-500/30 text-blue-200 hover:border-cyan-400/60 hover:text-white hover:bg-[#06183d]'
            }`}
            title={isPlayingBriefing ? 'Pausar narração do briefing' : 'Reproduzir briefing de cards'}
          >
            {isPlayingBriefing ? (
              <>
                <Pause className="w-3.5 h-3.5 text-cyan-300" />
                <span className="hidden sm:inline">PAUSAR</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 text-cyan-300" />
                <span className="hidden sm:inline">BRIEFING</span>
              </>
            )}
          </button>
        )}

        {/* Audio narration mute/unmute toggle */}
        {onToggleAudioVoice && (
          <button
            onClick={onToggleAudioVoice}
            className={`p-2 rounded-full border transition-all cursor-pointer shadow-md ${
              isAudioVoiceEnabled
                ? 'bg-[#040e24]/80 border-cyan-500/35 text-cyan-300 hover:bg-[#06183d]'
                : 'bg-[#040e24]/60 border-blue-900/40 text-blue-400/40 hover:text-blue-300'
            }`}
            title={isAudioVoiceEnabled ? 'Voz sintética ativada' : 'Voz sintética silenciada'}
          >
            {isAudioVoiceEnabled ? (
              <Volume2 className="w-3.5 h-3.5" />
            ) : (
              <VolumeX className="w-3.5 h-3.5" />
            )}
          </button>
        )}
      </div>
    </footer>
  );
};
