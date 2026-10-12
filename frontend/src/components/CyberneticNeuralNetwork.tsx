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

interface CyberneticNeuralNetworkProps {
  state: CronosState;
  onVoiceClick?: () => void;
  className?: string;
}

interface FunctionModule {
  id: string;
  index: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'red' | 'cyan';
  pathColor: string;
  coreStroke: string;
  telemetryType: 'dots' | 'wave' | 'bars' | 'segments';
  junctionPercent?: number;
}

export const CyberneticNeuralNetwork: React.FC<CyberneticNeuralNetworkProps> = ({
  state,
  onVoiceClick,
  className = '',
}) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const modules: FunctionModule[] = [
    {
      id: 'm-01',
      index: '01',
      label: 'PROCESSAMENTO',
      icon: Cpu,
      color: 'cyan',
      pathColor: '#00f0ff',
      coreStroke: '#e0ffff',
      telemetryType: 'dots',
      junctionPercent: 0.62,
    },
    {
      id: 'm-02',
      index: '02',
      label: 'VISÃO COMPUTACIONAL',
      icon: Eye,
      color: 'red',
      pathColor: '#ff2255',
      coreStroke: '#ffd6e0',
      telemetryType: 'bars',
    },
    {
      id: 'm-03',
      index: '03',
      label: 'SÍNTESE DE VOZ',
      icon: AudioWaveform,
      color: 'red',
      pathColor: '#ff2255',
      coreStroke: '#ffd6e0',
      telemetryType: 'wave',
      junctionPercent: 0.32,
    },
    {
      id: 'm-04',
      index: '04',
      label: 'ENTENDIMENTO DE LINGUAGEM',
      icon: MessageSquare,
      color: 'cyan',
      pathColor: '#00f0ff',
      coreStroke: '#e0ffff',
      telemetryType: 'dots',
    },
    {
      id: 'm-05',
      index: '05',
      label: 'PLANEJAMENTO',
      icon: Crosshair,
      color: 'red',
      pathColor: '#ff2255',
      coreStroke: '#ffd6e0',
      telemetryType: 'segments',
      junctionPercent: 0.46,
    },
    {
      id: 'm-06',
      index: '06',
      label: 'FERRAMENTAS',
      icon: Settings,
      color: 'red',
      pathColor: '#ff2255',
      coreStroke: '#ffd6e0',
      telemetryType: 'dots',
    },
    {
      id: 'm-07',
      index: '07',
      label: 'INTEGRAÇÕES',
      icon: Plug,
      color: 'cyan',
      pathColor: '#00f0ff',
      coreStroke: '#e0ffff',
      telemetryType: 'dots',
      junctionPercent: 0.68,
    },
    {
      id: 'm-08',
      index: '08',
      label: 'BANCO DE DADOS',
      icon: Database,
      color: 'cyan',
      pathColor: '#00f0ff',
      coreStroke: '#e0ffff',
      telemetryType: 'bars',
    },
    {
      id: 'm-09',
      index: '09',
      label: 'INTERNET',
      icon: Globe,
      color: 'cyan',
      pathColor: '#00f0ff',
      coreStroke: '#e0ffff',
      telemetryType: 'segments',
      junctionPercent: 0.54,
    },
    {
      id: 'm-10',
      index: '10',
      label: 'DISPOSITIVOS',
      icon: MonitorSmartphone,
      color: 'cyan',
      pathColor: '#00f0ff',
      coreStroke: '#e0ffff',
      telemetryType: 'dots',
    },
    {
      id: 'm-11',
      index: '11',
      label: 'SEGURANÇA',
      icon: ShieldCheck,
      color: 'cyan',
      pathColor: '#00f0ff',
      coreStroke: '#e0ffff',
      telemetryType: 'bars',
      junctionPercent: 0.44,
    },
    {
      id: 'm-12',
      index: '12',
      label: 'MONITORAMENTO',
      icon: Activity,
      color: 'cyan',
      pathColor: '#00f0ff',
      coreStroke: '#e0ffff',
      telemetryType: 'segments',
    },
  ];

  // Fine purple/violet filaments that weave in the middle (exact detail from the photo)
  const purpleFilaments = [
    { startYOffset: -4, cp1X: 120, cp1Y: 85, cp2X: 240, cp2Y: 155, endX: 340, endY: 172 },
    { startYOffset: 2, cp1X: 135, cp1Y: 110, cp2X: 260, cp2Y: 220, endX: 340, endY: 244 },
    { startYOffset: 8, cp1X: 110, cp1Y: 140, cp2X: 230, cp2Y: 275, endX: 340, endY: 280 },
    { startYOffset: 14, cp1X: 145, cp1Y: 170, cp2X: 250, cp2Y: 330, endX: 340, endY: 352 },
  ];

  // SVG dimensions for the bus network:
  // Starts near the hub at X=40, Y=180
  const hubOriginX = 42;
  const hubOriginY = 175;
  const targetX = 350;

  return (
    <div
      className={`relative flex items-center select-none pointer-events-auto ${className}`}
      style={{ maxHeight: '92vh' }}
    >
      {/* SVG Canvas for Glowing Fiber Lines, Purple Filaments & Ambient HUD circuits */}
      <div className="relative w-[350px] h-[580px] hidden xl:block shrink-0 pointer-events-none overflow-visible">
        <svg
          viewBox="0 0 350 580"
          className="w-full h-full overflow-visible"
          fill="none"
        >
          <defs>
            {/* Multi-layered intense neon blur filters */}
            <filter id="intenseNeonRed" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3.5" result="glow1" />
              <feGaussianBlur stdDeviation="1.5" result="glow2" />
              <feMerge>
                <feMergeNode in="glow1" />
                <feMergeNode in="glow2" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <filter id="intenseNeonCyan" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3.5" result="glow1" />
              <feGaussianBlur stdDeviation="1.5" result="glow2" />
              <feMerge>
                <feMergeNode in="glow1" />
                <feMergeNode in="glow2" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            <filter id="intenseNeonPurple" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="2.8" result="glow1" />
              <feMerge>
                <feMergeNode in="glow1" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* 1. Cybernetic Ambient Grid & Circuit Elements (from photo background) */}
          <g opacity="0.45" stroke="#00f0ff" strokeWidth="0.8">
            {/* Crosshair target near hub */}
            <path d="M 15 130 H 30 M 22 122 V 138" strokeWidth="1" />
            <circle cx="22" cy="130" r="12" strokeDasharray="3 3" />

            {/* Circuit step traces with 90° bends */}
            <path d="M 60 70 H 110 L 130 90 H 160" />
            <circle cx="160" cy="90" r="1.8" fill="#00f0ff" />
            <path d="M 40 310 L 70 340 H 110 L 130 360 H 170" />
            <circle cx="170" cy="360" r="1.8" fill="#00f0ff" />

            {/* Dot matrix telemetry clusters */}
            {[
              [80, 50],
              [90, 50],
              [100, 50],
              [80, 56],
              [90, 56],
              [100, 56],
              [140, 480],
              [150, 480],
              [160, 480],
              [140, 486],
              [150, 486],
              [160, 486],
            ].map(([x, y], idx) => (
              <circle key={idx} cx={x} cy={y} r="0.9" fill="#00f0ff" />
            ))}
          </g>

          {/* 2. Delicate Purple/Violet Filaments (exact detail requested by user) */}
          {purpleFilaments.map((fil, idx) => {
            const startY = hubOriginY + fil.startYOffset;
            const pathD = `M ${hubOriginX} ${startY} C ${fil.cp1X} ${fil.cp1Y}, ${fil.cp2X} ${fil.cp2Y}, ${fil.endX} ${fil.endY}`;
            return (
              <g key={`purple-${idx}`}>
                {/* Glowing purple ambient stroke */}
                <path
                  d={pathD}
                  stroke="#c084fc"
                  strokeWidth="1.8"
                  strokeOpacity="0.75"
                  filter="url(#intenseNeonPurple)"
                />
                {/* Fine crisp center thread */}
                <path
                  d={pathD}
                  stroke="#f5d0fe"
                  strokeWidth="0.7"
                  strokeOpacity="0.9"
                />
                {/* Purple glowing data pulse */}
                <circle r="1.8" fill="#f0abfc" filter="url(#intenseNeonPurple)">
                  <animateMotion
                    path={pathD}
                    dur={`${2.4 + idx * 0.4}s`}
                    repeatCount="indefinite"
                    begin={`${idx * 0.3}s`}
                  />
                </circle>
                {/* Intermediate purple node */}
                <circle
                  cx={(hubOriginX + fil.endX) * 0.5 + idx * 8}
                  cy={(startY + fil.endY) * 0.52}
                  r="2.2"
                  fill="#c084fc"
                  stroke="#ffffff"
                  strokeWidth="0.8"
                  filter="url(#intenseNeonPurple)"
                />
              </g>
            );
          })}

          {/* 3. Primary Red and Cyan Glowing Conduits fanning into each Module */}
          {modules.map((mod, idx) => {
            const destY = 24 + idx * 45;
            const isRed = mod.color === 'red';
            const isHovered = hoveredId === mod.id;
            const isVoiceActive =
              state === 'SPEAKING' &&
              (mod.id === 'm-03' || mod.id === 'm-01' || mod.id === 'm-04');

            // Cubic Bezier curve matching the image flow:
            // Starts near the hub, curves downwards/upwards gracefully, and levels horizontally into target
            const cp1X = hubOriginX + 85 + (idx % 3) * 12;
            const cp1Y = hubOriginY + (destY - hubOriginY) * 0.2;
            const cp2X = targetX - 90 - (idx % 2) * 15;
            const cp2Y = destY;

            const pathD = `M ${hubOriginX} ${hubOriginY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${targetX} ${destY}`;

            return (
              <g key={mod.id}>
                {/* Wide soft neon bloom stroke */}
                <path
                  d={pathD}
                  stroke={mod.pathColor}
                  strokeWidth={isHovered || isVoiceActive ? 4.5 : 2.5}
                  strokeOpacity={
                    isVoiceActive
                      ? 1.0
                      : isHovered
                      ? 0.95
                      : isRed
                      ? 0.75
                      : 0.65
                  }
                  filter={isRed ? 'url(#intenseNeonRed)' : 'url(#intenseNeonCyan)'}
                />

                {/* Second concentrated neon stroke */}
                <path
                  d={pathD}
                  stroke={mod.pathColor}
                  strokeWidth={isHovered || isVoiceActive ? 2.0 : 1.2}
                  strokeOpacity={0.9}
                />

                {/* Inner white-hot wire core */}
                <path
                  d={pathD}
                  stroke={mod.coreStroke}
                  strokeWidth={0.7}
                  strokeOpacity={isHovered || isVoiceActive ? 1.0 : 0.75}
                />

                {/* Primary Photonic Data Packet gliding along path */}
                <circle
                  r={isVoiceActive ? 3.2 : 2.2}
                  fill={isRed ? '#ffe4e6' : '#ffffff'}
                  filter={isRed ? 'url(#intenseNeonRed)' : 'url(#intenseNeonCyan)'}
                >
                  <animateMotion
                    path={pathD}
                    dur={`${1.9 + (idx % 4) * 0.35}s`}
                    repeatCount="indefinite"
                    begin={`${idx * 0.14}s`}
                  />
                </circle>

                {/* Secondary smaller particle */}
                <circle
                  r={1.4}
                  fill={mod.pathColor}
                  filter={isRed ? 'url(#intenseNeonRed)' : 'url(#intenseNeonCyan)'}
                >
                  <animateMotion
                    path={pathD}
                    dur={`${2.6 + (idx % 3) * 0.4}s`}
                    repeatCount="indefinite"
                    begin={`${idx * 0.22 + 1.1}s`}
                  />
                </circle>

                {/* Intermediate Glowing Junction Bead (matching reference photo) */}
                {mod.junctionPercent && (
                  <circle
                    cx={hubOriginX + (targetX - hubOriginX) * mod.junctionPercent}
                    cy={hubOriginY + (destY - hubOriginY) * Math.pow(mod.junctionPercent, 1.35)}
                    r={isVoiceActive ? 3.6 : 2.8}
                    fill={mod.pathColor}
                    stroke="#ffffff"
                    strokeWidth={1}
                    filter={isRed ? 'url(#intenseNeonRed)' : 'url(#intenseNeonCyan)'}
                  />
                )}

                {/* Terminal anchor dot before badge */}
                <circle
                  cx={targetX}
                  cy={destY}
                  r={2.8}
                  fill={mod.pathColor}
                  stroke="#ffffff"
                  strokeWidth={0.9}
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* 4. High-Tech Chamfered Module Function Cards (Matching Photo's Distinctive Boxes) */}
      <div className="flex flex-col gap-2 py-1 w-[260px] sm:w-[290px]">
        {modules.map((mod) => {
          const isRed = mod.color === 'red';
          const isHovered = hoveredId === mod.id;
          const isVoiceSpeaking =
            state === 'SPEAKING' &&
            (mod.id === 'm-03' || mod.id === 'm-01' || mod.id === 'm-04');
          const Icon = mod.icon;

          return (
            <div
              key={mod.id}
              onMouseEnter={() => setHoveredId(mod.id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => {
                if (mod.id === 'm-03' && onVoiceClick) {
                  onVoiceClick();
                }
              }}
              className={`group relative flex items-center justify-between px-2.5 py-1.5 transition-all duration-300 cursor-pointer ${
                isVoiceSpeaking
                  ? isRed
                    ? 'bg-rose-950/60 border border-rose-500/80 shadow-[0_0_20px_rgba(255,34,85,0.45)]'
                    : 'bg-cyan-950/60 border border-cyan-400/80 shadow-[0_0_20px_rgba(0,240,255,0.45)]'
                  : isHovered
                  ? isRed
                    ? 'bg-[#180309]/80 border border-rose-500/50 shadow-[0_0_12px_rgba(255,34,85,0.3)]'
                    : 'bg-[#03132e]/80 border border-cyan-500/50 shadow-[0_0_12px_rgba(0,240,255,0.3)]'
                  : 'bg-[#010614]/65 border border-blue-900/35 hover:border-blue-500/35'
              }`}
              style={{
                clipPath:
                  'polygon(0% 0%, calc(100% - 10px) 0%, 100% 10px, 100% 100%, 10px 100%, 0% calc(100% - 10px))',
              }}
            >
              {/* Left: Circular Badge with Double Glowing Ring and Icon */}
              <div className="flex items-center gap-2.5 min-w-0">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 border transition-all duration-300 ${
                    isRed
                      ? isVoiceSpeaking
                        ? 'bg-rose-950 border-rose-400 text-rose-200 shadow-[0_0_12px_#ff2255]'
                        : 'bg-[#1b0208] border-rose-500/60 text-rose-400 group-hover:border-rose-400 group-hover:text-rose-200'
                      : isVoiceSpeaking
                      ? 'bg-cyan-950 border-cyan-400 text-cyan-200 shadow-[0_0_12px_#00f0ff]'
                      : 'bg-[#021028] border-cyan-500/50 text-cyan-300 group-hover:border-cyan-400 group-hover:text-cyan-100'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>

                {/* Module Title */}
                <span
                  className={`text-[10px] font-mono tracking-wider truncate font-semibold transition-colors ${
                    isRed
                      ? isVoiceSpeaking
                        ? 'text-rose-200'
                        : 'text-rose-400/90 group-hover:text-rose-200'
                      : isVoiceSpeaking
                      ? 'text-cyan-200'
                      : 'text-slate-200 group-hover:text-cyan-200'
                  }`}
                >
                  {mod.label}
                </span>
              </div>

              {/* Right: Technical Telemetry Chamfer Bracket & Index Number */}
              <div className="flex items-center gap-2 shrink-0 pl-1">
                {/* Specific telemetry types matching the reference photo */}
                {mod.id === 'm-03' ? (
                  /* Audio waveform equalizer */
                  <div className="flex items-center gap-0.5 h-3.5">
                    <span
                      className={`w-0.5 bg-rose-400 rounded-full ${
                        state === 'SPEAKING' ? 'h-3 animate-bounce' : 'h-1.5'
                      }`}
                    />
                    <span
                      className={`w-0.5 bg-rose-300 rounded-full ${
                        state === 'SPEAKING' ? 'h-3.5 animate-pulse' : 'h-2.5'
                      }`}
                    />
                    <span
                      className={`w-0.5 bg-rose-400 rounded-full ${
                        state === 'SPEAKING' ? 'h-2 animate-bounce' : 'h-1'
                      }`}
                    />
                  </div>
                ) : mod.telemetryType === 'segments' ? (
                  /* Segmented mini telemetry bars */
                  <div className="flex items-center gap-0.5 opacity-60 group-hover:opacity-100">
                    <span className="w-1 h-2 bg-rose-400/80 rounded-xs" />
                    <span className="w-1 h-2 bg-rose-400/80 rounded-xs" />
                    <span className="w-1 h-2 bg-rose-400/50 rounded-xs" />
                    <span className="w-1 h-2 bg-rose-400/20 rounded-xs" />
                  </div>
                ) : mod.telemetryType === 'bars' ? (
                  /* Horizontal telemetry bar */
                  <div className="w-6 h-1 rounded-full bg-blue-950 overflow-hidden border border-cyan-500/30">
                    <div className="w-3.5 h-full bg-cyan-400" />
                  </div>
                ) : (
                  /* Dot matrix (::: :) */
                  <div className="flex items-center gap-0.5 opacity-40 group-hover:opacity-90">
                    <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                    <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                    <span className="w-0.5 h-0.5 rounded-full bg-cyan-400" />
                  </div>
                )}

                {/* Index number with mini tech box */}
                <div className="flex items-center gap-1 font-mono text-[9px] text-slate-400 tabular-nums">
                  <span className="w-1.5 h-1.5 border border-cyan-400/50 rounded-2xs inline-block" />
                  <span className="group-hover:text-cyan-300">{mod.index}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
