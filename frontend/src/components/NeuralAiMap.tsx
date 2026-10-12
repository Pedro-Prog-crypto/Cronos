import React, { useState } from 'react';
import {
  Cpu,
  Eye,
  AudioWaveform,
  MessageSquare,
  Crosshair,
  Settings,
  Plug,
  Database,
  Globe,
  MonitorSmartphone,
  ShieldCheck,
  Activity,
} from 'lucide-react';
import { CronosState } from '../types/cronos';

interface NeuralAiMapProps {
  state: CronosState;
  onVoiceNodeClick?: () => void;
  className?: string;
}

interface NeuralNode {
  id: string;
  index: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'cyan' | 'red' | 'blue' | 'purple';
  activeDuringSpeech?: boolean;
}

export const NeuralAiMap: React.FC<NeuralAiMapProps> = ({
  state,
  onVoiceNodeClick,
  className = '',
}) => {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const nodes: NeuralNode[] = [
    {
      id: 'n-01',
      index: '01',
      label: 'PROCESSAMENTO',
      icon: Cpu,
      color: 'cyan',
      activeDuringSpeech: true,
    },
    {
      id: 'n-02',
      index: '02',
      label: 'VISÃO COMPUTACIONAL',
      icon: Eye,
      color: 'red',
    },
    {
      id: 'n-03',
      index: '03',
      label: 'SÍNTESE DE VOZ',
      icon: AudioWaveform,
      color: 'red',
      activeDuringSpeech: true,
    },
    {
      id: 'n-04',
      index: '04',
      label: 'ENTENDIMENTO DE LINGUAGEM',
      icon: MessageSquare,
      color: 'cyan',
      activeDuringSpeech: true,
    },
    {
      id: 'n-05',
      index: '05',
      label: 'PLANEJAMENTO',
      icon: Crosshair,
      color: 'red',
    },
    {
      id: 'n-06',
      index: '06',
      label: 'FERRAMENTAS',
      icon: Settings,
      color: 'red',
    },
    {
      id: 'n-07',
      index: '07',
      label: 'INTEGRAÇÕES',
      icon: Plug,
      color: 'cyan',
    },
    {
      id: 'n-08',
      index: '08',
      label: 'BANCO DE DADOS',
      icon: Database,
      color: 'cyan',
    },
    {
      id: 'n-09',
      index: '09',
      label: 'INTERNET',
      icon: Globe,
      color: 'cyan',
    },
    {
      id: 'n-10',
      index: '10',
      label: 'DISPOSITIVOS',
      icon: MonitorSmartphone,
      color: 'cyan',
    },
    {
      id: 'n-11',
      index: '11',
      label: 'SEGURANÇA',
      icon: ShieldCheck,
      color: 'cyan',
    },
    {
      id: 'n-12',
      index: '12',
      label: 'MONITORAMENTO',
      icon: Activity,
      color: 'cyan',
    },
  ];

  // SVG parameters for the flowing fiber optic lines:
  // Height = 460px, width = 90px
  const svgHeight = 460;
  const startX = 0;
  const startY = svgHeight / 2; // Lines originate from center-left near the core
  const endX = 85;

  return (
    <div
      className={`relative flex items-center select-none pointer-events-auto ${className}`}
      style={{ maxHeight: '90vh' }}
    >
      {/* Curved Fiber Optic Bus Lines (SVG) */}
      <div className="relative w-[85px] h-[460px] hidden md:block shrink-0 pointer-events-none">
        <svg
          viewBox={`0 0 85 ${svgHeight}`}
          className="w-full h-full overflow-visible"
          fill="none"
        >
          <defs>
            <linearGradient id="fiberCyanGrad" x1="0%" y1="50%" x2="100%" y2="50%">
              <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.8" />
              <stop offset="60%" stopColor="#0284c7" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.9" />
            </linearGradient>

            <linearGradient id="fiberRedGrad" x1="0%" y1="50%" x2="100%" y2="50%">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.8" />
              <stop offset="60%" stopColor="#e11d48" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#fb7185" stopOpacity="0.9" />
            </linearGradient>

            {/* Glowing filter */}
            <filter id="fiberGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="1.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {nodes.map((node, idx) => {
            // Target Y for this node's circle
            const nodeY = 18 + idx * 36;
            const isRed = node.color === 'red';
            const isHovered = hoveredNodeId === node.id;
            const isVoiceSpeaking =
              state === 'SPEAKING' && Boolean(node.activeDuringSpeech);

            // Smooth S-curve bezier path from core to node
            const d = `M ${startX} ${startY} C ${startX + 35} ${startY}, ${endX - 35} ${nodeY}, ${endX} ${nodeY}`;

            return (
              <g key={node.id}>
                {/* Background glow path */}
                <path
                  d={d}
                  stroke={isRed ? '#f43f5e' : '#00f0ff'}
                  strokeWidth={isHovered || isVoiceSpeaking ? 2.5 : 1.2}
                  strokeOpacity={
                    isVoiceSpeaking
                      ? 0.95
                      : isHovered
                      ? 0.8
                      : isRed
                      ? 0.35
                      : 0.25
                  }
                  filter="url(#fiberGlow)"
                  fill="none"
                />

                {/* Animated Photonic Data Particle flowing along the path */}
                <circle
                  r={isVoiceSpeaking ? 2.4 : 1.6}
                  fill={isRed ? '#fda4af' : '#e0faff'}
                  filter="url(#fiberGlow)"
                >
                  <animateMotion
                    path={d}
                    dur={`${2.2 + (idx % 4) * 0.4}s`}
                    repeatCount="indefinite"
                    begin={`${idx * 0.18}s`}
                  />
                </circle>

                {/* Target node anchor dot */}
                <circle
                  cx={endX}
                  cy={nodeY}
                  r={2.5}
                  fill={isRed ? '#f43f5e' : '#00f0ff'}
                  stroke="#ffffff"
                  strokeWidth="0.7"
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Vertical Stack of Module Nodes */}
      <div className="flex flex-col gap-[7px] py-1 w-[220px] sm:w-[245px]">
        {nodes.map((node) => {
          const isRed = node.color === 'red';
          const isHovered = hoveredNodeId === node.id;
          const isSpeakingActive =
            state === 'SPEAKING' && Boolean(node.activeDuringSpeech);
          const Icon = node.icon;

          return (
            <div
              key={node.id}
              onMouseEnter={() => setHoveredNodeId(node.id)}
              onMouseLeave={() => setHoveredNodeId(null)}
              onClick={() => {
                if (node.id === 'n-03' && onVoiceNodeClick) {
                  onVoiceNodeClick();
                }
              }}
              className={`group flex items-center justify-between px-2 py-1 rounded-lg transition-all duration-300 cursor-pointer ${
                isSpeakingActive
                  ? isRed
                    ? 'bg-rose-950/40 border border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.35)]'
                    : 'bg-cyan-950/40 border border-cyan-400/60 shadow-[0_0_15px_rgba(0,229,255,0.35)]'
                  : isHovered
                  ? 'bg-[#03132e]/70 border border-cyan-500/35'
                  : 'bg-[#010816]/50 border border-transparent hover:border-blue-500/20'
              }`}
            >
              {/* Left: Circular Icon Badge */}
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border transition-all duration-300 ${
                    isRed
                      ? isSpeakingActive
                        ? 'bg-rose-950 border-rose-400 text-rose-300 shadow-[0_0_8px_#f43f5e]'
                        : 'bg-[#18040a] border-rose-500/40 text-rose-400/80 group-hover:border-rose-400 group-hover:text-rose-200'
                      : isSpeakingActive
                      ? 'bg-cyan-950 border-cyan-400 text-cyan-200 shadow-[0_0_8px_#00e5ff]'
                      : 'bg-[#021026] border-cyan-500/35 text-cyan-400/80 group-hover:border-cyan-400 group-hover:text-cyan-200'
                  }`}
                >
                  <Icon className="w-3.2 h-3.2" />
                </div>

                {/* Node Label */}
                <span
                  className={`text-[10px] font-mono tracking-wider truncate font-medium transition-colors ${
                    isRed
                      ? isSpeakingActive
                        ? 'text-rose-200 font-semibold'
                        : 'text-rose-400/90 group-hover:text-rose-200'
                      : isSpeakingActive
                      ? 'text-cyan-200 font-semibold'
                      : 'text-slate-300/85 group-hover:text-cyan-200'
                  }`}
                >
                  {node.label}
                </span>
              </div>

              {/* Right: Technical Index & Mini Wave / Dot Matrix */}
              <div className="flex items-center gap-1.5 shrink-0 pl-1">
                {/* Voice Equalizer animation when active */}
                {node.id === 'n-03' && state === 'SPEAKING' ? (
                  <div className="flex items-center gap-0.5 h-3">
                    <span className="w-0.5 h-2.5 bg-rose-400 rounded-full animate-pulse" />
                    <span className="w-0.5 h-3 bg-rose-300 rounded-full animate-bounce" />
                    <span className="w-0.5 h-1.5 bg-rose-400 rounded-full animate-pulse" />
                  </div>
                ) : (
                  /* Discreet Tech Dots */
                  <div className="hidden sm:flex items-center gap-0.5 opacity-40 group-hover:opacity-80 transition-opacity">
                    <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                    <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                    <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                  </div>
                )}

                {/* Index number */}
                <span className="text-[9px] font-mono tabular-nums text-slate-500 group-hover:text-blue-300/70">
                  {node.index}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
