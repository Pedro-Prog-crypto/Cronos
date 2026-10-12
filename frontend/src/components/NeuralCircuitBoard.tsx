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
import { StellarCore } from './StellarCore';
import { CronosLogo } from './CronosLogo';
import { CronosState } from '../types/cronos';
import bgSpace from '../assets/images/deep_space_void_1791823511313.jpg';

interface NeuralCircuitBoardProps {
  state: CronosState;
  audioLevel?: number;
  onMicToggle?: () => void;
  className?: string;
}

interface NodeItem {
  id: string;
  index: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'red' | 'cyan';
  pathColor: string;
  glowColor: string;
  junctionNode?: { progress: number }; // along path
}

export const NeuralCircuitBoard: React.FC<NeuralCircuitBoardProps> = ({
  state,
  audioLevel = 0,
  onMicToggle,
  className = '',
}) => {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const nodes: NodeItem[] = [
    {
      id: 'n-01',
      index: '01',
      label: 'PROCESSAMENTO',
      icon: Cpu,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      junctionNode: { progress: 0.65 },
    },
    {
      id: 'n-02',
      index: '02',
      label: 'VISÃO COMPUTACIONAL',
      icon: Eye,
      color: 'red',
      pathColor: '#ff2d55',
      glowColor: '#ff2d55',
    },
    {
      id: 'n-03',
      index: '03',
      label: 'SÍNTESE DE VOZ',
      icon: AudioWaveform,
      color: 'red',
      pathColor: '#ff2d55',
      glowColor: '#ff2d55',
      junctionNode: { progress: 0.35 },
    },
    {
      id: 'n-04',
      index: '04',
      label: 'ENTENDIMENTO DE LINGUAGEM',
      icon: MessageSquare,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
    },
    {
      id: 'n-05',
      index: '05',
      label: 'PLANEJAMENTO',
      icon: Crosshair,
      color: 'red',
      pathColor: '#ff2d55',
      glowColor: '#ff2d55',
      junctionNode: { progress: 0.5 },
    },
    {
      id: 'n-06',
      index: '06',
      label: 'FERRAMENTAS',
      icon: Settings,
      color: 'red',
      pathColor: '#ff2d55',
      glowColor: '#ff2d55',
    },
    {
      id: 'n-07',
      index: '07',
      label: 'INTEGRAÇÕES',
      icon: Plug,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      junctionNode: { progress: 0.68 },
    },
    {
      id: 'n-08',
      index: '08',
      label: 'BANCO DE DADOS',
      icon: Database,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
    },
    {
      id: 'n-09',
      index: '09',
      label: 'INTERNET',
      icon: Globe,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      junctionNode: { progress: 0.55 },
    },
    {
      id: 'n-10',
      index: '10',
      label: 'DISPOSITIVOS',
      icon: MonitorSmartphone,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
    },
    {
      id: 'n-11',
      index: '11',
      label: 'SEGURANÇA',
      icon: ShieldCheck,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      junctionNode: { progress: 0.42 },
    },
    {
      id: 'n-12',
      index: '12',
      label: 'MONITORAMENTO',
      icon: Activity,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
    },
  ];

  // Canvas coordinates for the SVG neural bus:
  // ViewBox: 1200 x 680
  // Star Core Center is around (260, 340)
  // Origin cluster on the right edge of star core is around (325, 335)
  const originX = 325;
  const originY = 340;
  const targetX = 930; // Where the fiber enters the node list

  return (
    <div
      className={`relative w-full h-full overflow-hidden select-none flex items-center justify-center ${className}`}
    >
      {/* Background: Deep Dark Cosmic Space Image with soft dark vignette */}
      <div
        className="absolute inset-0 bg-cover bg-center opacity-85 pointer-events-none"
        style={{ backgroundImage: `url(${bgSpace})` }}
      />
      <div className="absolute inset-0 bg-radial-gradient from-transparent via-black/40 to-black/90 pointer-events-none" />

      {/* Main Responsive Grid Container */}
      <div className="relative w-full max-w-[1400px] h-[92vh] max-h-[720px] mx-auto flex items-center justify-between px-4 sm:px-8 z-10">
        {/* LEFT COLUMN: Stellar Super-Bright Core + CRONOS Neon Logo */}
        <div className="relative flex flex-col items-center justify-center shrink-0 z-20 w-[340px] sm:w-[380px]">
          <StellarCore
            state={state}
            audioLevel={audioLevel}
            onClick={onMicToggle}
            size={340}
          />

          {/* CRONOS Neon Blue Logo below the star core */}
          <div className="-mt-6 flex flex-col items-center">
            <CronosLogo
              isSpeaking={state === 'SPEAKING'}
              size="sm"
            />
          </div>
        </div>

        {/* MIDDLE: SVG Flowing Neural Bus Lines (Curved Fiber Optic Cables) */}
        <div className="absolute inset-0 w-full h-full pointer-events-none z-15 hidden lg:block">
          <svg
            viewBox="0 0 1200 680"
            className="w-full h-full overflow-visible"
            fill="none"
          >
            <defs>
              <filter id="busGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="2.5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {nodes.map((node, idx) => {
              // Target Y for this module (distributed evenly between Y=70 and Y=610)
              const destY = 72 + idx * 48;
              const isHovered = hoveredNodeId === node.id;
              const isVoiceSpeaking =
                state === 'SPEAKING' &&
                (node.id === 'n-03' || node.id === 'n-01' || node.id === 'n-04');

              // The exact S-curve matching the reference image:
              // Emerges horizontally from the core right-edge, branches upwards/downwards, and settles horizontally into the node
              const cp1X = originX + 110 + (idx % 3) * 15;
              const cp1Y = originY + (destY - originY) * 0.15;
              const cp2X = targetX - 140 - (idx % 2) * 20;
              const cp2Y = destY;

              const pathD = `M ${originX} ${originY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${targetX} ${destY}`;

              return (
                <g key={node.id}>
                  {/* Outer glow stroke */}
                  <path
                    d={pathD}
                    stroke={node.pathColor}
                    strokeWidth={isHovered || isVoiceSpeaking ? 3.2 : 1.6}
                    strokeOpacity={
                      isVoiceSpeaking
                        ? 0.95
                        : isHovered
                        ? 0.9
                        : node.color === 'red'
                        ? 0.55
                        : 0.35
                    }
                    filter="url(#busGlow)"
                    fill="none"
                  />

                  {/* Inner crisp line */}
                  <path
                    d={pathD}
                    stroke={node.color === 'red' ? '#ffccd5' : '#e0ffff'}
                    strokeWidth={0.8}
                    strokeOpacity={isHovered || isVoiceSpeaking ? 0.95 : 0.6}
                    fill="none"
                  />

                  {/* Animated Photonic Data Packet gliding along this cable */}
                  <circle
                    r={isVoiceSpeaking ? 2.8 : 2.0}
                    fill={node.color === 'red' ? '#ffe4e6' : '#ffffff'}
                    filter="url(#busGlow)"
                  >
                    <animateMotion
                      path={pathD}
                      dur={`${2.0 + (idx % 4) * 0.35}s`}
                      repeatCount="indefinite"
                      begin={`${idx * 0.15}s`}
                    />
                  </circle>

                  {/* Secondary particle */}
                  <circle
                    r={1.5}
                    fill={node.pathColor}
                    filter="url(#busGlow)"
                  >
                    <animateMotion
                      path={pathD}
                      dur={`${2.8 + (idx % 3) * 0.5}s`}
                      repeatCount="indefinite"
                      begin={`${idx * 0.25 + 1.2}s`}
                    />
                  </circle>

                  {/* Junction node circle along the line (if configured) */}
                  {node.junctionNode && (
                    <g>
                      {/* We compute an approximate mid-point for the visual junction */}
                      <circle
                        cx={originX + (targetX - originX) * node.junctionNode.progress}
                        cy={originY + (destY - originY) * Math.pow(node.junctionNode.progress, 1.4)}
                        r={3.2}
                        fill={node.pathColor}
                        stroke="#ffffff"
                        strokeWidth={1}
                        filter="url(#busGlow)"
                      />
                    </g>
                  )}

                  {/* Terminal dot before node icon */}
                  <circle
                    cx={targetX}
                    cy={destY}
                    r={3}
                    fill={node.pathColor}
                    stroke="#ffffff"
                    strokeWidth={1}
                  />
                </g>
              );
            })}
          </svg>
        </div>

        {/* RIGHT COLUMN: 12 Neural AI Module Nodes */}
        <div className="relative flex flex-col gap-1.5 sm:gap-2 shrink-0 z-20 w-[240px] sm:w-[275px]">
          {nodes.map((node) => {
            const isRed = node.color === 'red';
            const isHovered = hoveredNodeId === node.id;
            const isSpeakingActive =
              state === 'SPEAKING' &&
              (node.id === 'n-03' || node.id === 'n-01' || node.id === 'n-04');
            const Icon = node.icon;

            return (
              <div
                key={node.id}
                onMouseEnter={() => setHoveredNodeId(node.id)}
                onMouseLeave={() => setHoveredNodeId(null)}
                onClick={() => {
                  if (node.id === 'n-03' && onMicToggle) {
                    onMicToggle();
                  }
                }}
                className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg transition-all duration-300 cursor-pointer ${
                  isSpeakingActive
                    ? isRed
                      ? 'bg-rose-950/50 border border-rose-500/70 shadow-[0_0_18px_rgba(244,63,94,0.4)]'
                      : 'bg-cyan-950/50 border border-cyan-400/70 shadow-[0_0_18px_rgba(0,229,255,0.4)]'
                    : isHovered
                    ? 'bg-[#03132e]/80 border border-cyan-500/40 shadow-[0_0_12px_rgba(0,180,255,0.2)]'
                    : 'bg-[#010614]/70 border border-blue-900/30 hover:border-blue-500/30'
                }`}
              >
                {/* Left: Icon inside glowing circle badge */}
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 border transition-all duration-300 ${
                      isRed
                        ? isSpeakingActive
                          ? 'bg-rose-950 border-rose-400 text-rose-200 shadow-[0_0_10px_#f43f5e]'
                          : 'bg-[#180309] border-rose-500/50 text-rose-400 group-hover:border-rose-400 group-hover:text-rose-200'
                        : isSpeakingActive
                        ? 'bg-cyan-950 border-cyan-400 text-cyan-200 shadow-[0_0_10px_#00e5ff]'
                        : 'bg-[#021028] border-cyan-500/40 text-cyan-300 group-hover:border-cyan-400 group-hover:text-cyan-100'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </div>

                  {/* Module Label */}
                  <span
                    className={`text-[10px] font-mono tracking-wider truncate font-medium transition-colors ${
                      isRed
                        ? isSpeakingActive
                          ? 'text-rose-200 font-semibold'
                          : 'text-rose-400/90 group-hover:text-rose-200'
                        : isSpeakingActive
                        ? 'text-cyan-200 font-semibold'
                        : 'text-slate-300 group-hover:text-cyan-200'
                    }`}
                  >
                    {node.label}
                  </span>
                </div>

                {/* Right: Technical Telemetry & Index Number */}
                <div className="flex items-center gap-2 shrink-0 pl-1">
                  {/* Waveform indicator for voice synthesis */}
                  {node.id === 'n-03' && state === 'SPEAKING' ? (
                    <div className="flex items-center gap-0.5 h-3">
                      <span className="w-0.5 h-2.5 bg-rose-400 rounded-full animate-pulse" />
                      <span className="w-0.5 h-3 bg-rose-300 rounded-full animate-bounce" />
                      <span className="w-0.5 h-1.5 bg-rose-400 rounded-full animate-pulse" />
                    </div>
                  ) : (
                    /* Subtle tech dots */
                    <div className="hidden sm:flex items-center gap-0.5 opacity-40 group-hover:opacity-85 transition-opacity">
                      <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                      <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                      <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                    </div>
                  )}

                  {/* Index number */}
                  <span className="text-[9px] font-mono tabular-nums text-slate-500 group-hover:text-blue-300/80">
                    {node.index}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
