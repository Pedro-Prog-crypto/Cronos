import React, { useMemo, useState } from 'react';
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
import { CronosOrb } from './CronosOrb';
import { CronosLogo } from './CronosLogo';
import { StellarCore } from './StellarCore';
import { CronosState } from '../types/cronos';
import bgSpace from '../assets/images/deep_space_void_1791823511313.jpg';

interface IntegratedNeuralStageProps {
  state: CronosState;
  audioLevelSource?: React.RefObject<number>;
  audioLevel?: number;
  onOrbClick?: () => void;
  onMicToggle?: () => void;
  onModuleClick?: (index: number) => void;
  className?: string;
}

interface FloatingFunctionNode {
  id: string;
  label: string;
  lines?: string[]; // optional multi-line label (e.g. for ENTENDIMENTO / DE LINGUAGEM)
  icon: React.ComponentType<{ className?: string }>;
  color: 'red' | 'cyan';
  pathColor: string;
  glowColor: string;
  coreColor: string;
  hasJunction?: boolean;
}

const Stage: React.FC<IntegratedNeuralStageProps> = ({
  state,
  audioLevel = 0,
  audioLevelSource,
  onOrbClick,
  onMicToggle,
  className = '',
  onModuleClick,
}) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Exactly 12 floating functions
  const functions: FloatingFunctionNode[] = [
    {
      id: 'fn-01',
      label: 'PROCESSAMENTO',
      icon: Cpu,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      coreColor: '#f0fdff',
      hasJunction: true,
    },
    {
      id: 'fn-02',
      label: 'VISÃO COMPUTACIONAL',
      icon: Eye,
      color: 'red',
      pathColor: '#ff2255',
      glowColor: '#ff2255',
      coreColor: '#fff1f2',
    },
    {
      id: 'fn-03',
      label: 'SÍNTESE DE VOZ',
      icon: AudioWaveform,
      color: 'red',
      pathColor: '#ff2255',
      glowColor: '#ff2255',
      coreColor: '#fff1f2',
      hasJunction: true,
    },
    {
      id: 'fn-04',
      label: 'ENTENDIMENTO DE LINGUAGEM',
      lines: ['ENTENDIMENTO', 'DE LINGUAGEM'], // Broken into two lines as requested
      icon: MessageSquare,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      coreColor: '#f0fdff',
    },
    {
      id: 'fn-05',
      label: 'PLANEJAMENTO',
      icon: Crosshair,
      color: 'red',
      pathColor: '#ff2255',
      glowColor: '#ff2255',
      coreColor: '#fff1f2',
      hasJunction: true,
    },
    {
      id: 'fn-06',
      label: 'FERRAMENTAS',
      icon: Settings,
      color: 'red',
      pathColor: '#ff2255',
      glowColor: '#ff2255',
      coreColor: '#fff1f2',
    },
    {
      id: 'fn-07',
      label: 'INTEGRAÇÕES',
      icon: Plug,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      coreColor: '#f0fdff',
      hasJunction: true,
    },
    {
      id: 'fn-08',
      label: 'BANCO DE DADOS',
      icon: Database,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      coreColor: '#f0fdff',
    },
    {
      id: 'fn-09',
      label: 'INTERNET',
      icon: Globe,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      coreColor: '#f0fdff',
      hasJunction: true,
    },
    {
      id: 'fn-10',
      label: 'DISPOSITIVOS',
      icon: MonitorSmartphone,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      coreColor: '#f0fdff',
    },
    {
      id: 'fn-11',
      label: 'SEGURANÇA',
      icon: ShieldCheck,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      coreColor: '#f0fdff',
      hasJunction: true,
    },
    {
      id: 'fn-12',
      label: 'MONITORAMENTO',
      icon: Activity,
      color: 'cyan',
      pathColor: '#00f0ff',
      glowColor: '#00f0ff',
      coreColor: '#f0fdff',
    },
  ];

  // SVG coordinate dimensions for the right-hand panel
  const svgWidth = 470;
  const svgHeight = 590;

  // Star center inside this right-hand SVG space (shifted right in harmony with functions):
  const starCx = 112;
  const starCy = 88;
  const starVisualSize = 210; // slightly increased size as requested

  // Functions shifted further right ("encoste mais para a direita"):
  const symbolX = 275;
  const symbolRadius = 10.5;
  const lineTouchX = symbolX - symbolRadius; // physically touches the left border of symbol ring

  // Unified trunk exit tangent leaving the center of the star towards the lower-right:
  const trunkExitX = starCx + 42;
  const trunkExitY = starCy + 26;

  // Rasterize stationary conduit bloom once per hover/state, rather than on every moving packet.
  const conduitBloom = useMemo(() => {
    const paths = functions.map((fn, idx) => {
      const y = 28 + idx * 45;
      const active = hoveredId === fn.id || (state === 'SPEAKING' && (idx === 0 || idx === 2));
      const d = `M ${starCx} ${starCy} C ${trunkExitX} ${trunkExitY}, ${lineTouchX - 54 - (idx % 2) * 8} ${y}, ${lineTouchX} ${y}`;
      return `<g stroke="${fn.pathColor}" fill="none" filter="url(#b)"><path d="${d}" stroke-width="${active ? 2.8 : 1.6}" opacity=".85"/><circle cx="${symbolX}" cy="${y}" r="${symbolRadius}" stroke-width="${active ? 1.4 : 1}"/></g>`;
    }).join('');
    return 'data:image/svg+xml,' + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="470" height="590" viewBox="0 0 470 590"><defs><filter id="b" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2.4" result="a"/><feGaussianBlur stdDeviation="1" result="c"/><feMerge><feMergeNode in="a"/><feMergeNode in="c"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>${paths}</svg>`);
  }, [hoveredId, state]);

  return (
    <div
      className={`relative w-full h-full overflow-hidden select-none ${className}`}
    >
      {/* 1. Deep Space Cosmic Background */}
      <div
        className="absolute inset-0 bg-cover bg-center opacity-85 pointer-events-none"
        style={{ backgroundImage: `url(${bgSpace})` }}
      />
      <div className="absolute inset-0 bg-radial-gradient from-transparent via-black/45 to-black/95 pointer-events-none" />

      {/* 2. CENTER STAGE: Approved CRONOS Woven Hologram & Neon Logo (Strictly Central) */}
      <div className="cronos-central-hologram absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 flex flex-col items-center justify-center pointer-events-auto">
        <CronosOrb
          state={state}
          audioLevel={audioLevel}
          audioLevelSource={audioLevelSource}
          onOrbClick={onOrbClick}
          size={440}
          weaveDensity={1.0}
          showCrossLinks={true}
        />

        {/* CRONOS Logo directly below the hologram */}
        <div className="-mt-7 flex flex-col items-center">
          <CronosLogo
            isSpeaking={state === 'SPEAKING'}
            size="sm"
          />
        </div>
      </div>

      {/* 3. RIGHT REGION: Encostado mais na direita, mantendo a proporção com a estrela */}
      <div className="absolute right-0 top-1/2 -translate-y-1/2 z-25 hidden lg:flex items-center justify-end pointer-events-auto pr-0 sm:pr-1">
        <div className="relative w-[470px] h-[590px] flex items-center justify-end">
          {/* THE SUPER-BRIGHT 3D CELESTIAL STAR (Slightly larger, matching image.png) */}
          <div
            className="absolute z-30 pointer-events-auto"
            style={{
              left: `${starCx - starVisualSize / 2}px`,
              top: `${starCy - starVisualSize / 2}px`,
              width: `${starVisualSize}px`,
              height: `${starVisualSize}px`,
            }}
          >
            <StellarCore
              state={state}
              audioLevel={audioLevel}
          audioLevelSource={audioLevelSource}
              onClick={onMicToggle}
              size={starVisualSize}
            />
          </div>

          {/* SVG FLOWING CONDUIT LINES:
              - Inside the star, all lines converge into a single trunk.
              - Approaching the star, they thin and merge into ONE line inside the star.
              - Enhanced luminosity / glow on all lines.
              - Data packets are blue, brighter, and larger as requested.
          */}
          <div className="absolute inset-0 w-full h-full pointer-events-auto z-20">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="w-full h-full overflow-visible"
              fill="none"
            >
              <defs>
                {/* Enhanced high-luminosity line glow filters */}
                <filter id="brilliantRedLineGlow" x="-40%" y="-40%" width="180%" height="180%">
                  <feGaussianBlur stdDeviation="2.4" result="blur1" />
                  <feGaussianBlur stdDeviation="1.0" result="blur2" />
                  <feMerge>
                    <feMergeNode in="blur1" />
                    <feMergeNode in="blur2" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>

                <filter id="brilliantCyanLineGlow" x="-40%" y="-40%" width="180%" height="180%">
                  <feGaussianBlur stdDeviation="2.4" result="blur1" />
                  <feGaussianBlur stdDeviation="1.0" result="blur2" />
                  <feMerge>
                    <feMergeNode in="blur1" />
                    <feMergeNode in="blur2" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>

                {/* Intense Electric Blue Glow for the moving Photonic Data Packets */}
                <radialGradient id="packet-light"><stop stopColor="#efffff"/><stop offset=".25" stopColor="#00f0ff" stopOpacity=".95"/><stop offset=".5" stopColor="#38bdf8" stopOpacity=".5"/><stop offset="1" stopColor="#00f0ff" stopOpacity="0"/></radialGradient>

                <filter id="textShadowGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="0" stdDeviation="2.2" floodColor="#000000" floodOpacity="0.9" />
                </filter>
              </defs>
              <image href={conduitBloom} width="470" height="590" pointerEvents="none" />

              {/* UNIFIED TRUNK INSIDE THE STAR:
                  Where all 12 lines are physically united into a single incandescent beam!
              */}
              <g className="pointer-events-none">
                {/* Luminous outer glow of the merged trunk */}
                <line
                  x1={starCx}
                  y1={starCy}
                  x2={trunkExitX}
                  y2={trunkExitY}
                  stroke="#00f0ff"
                  strokeWidth={state === 'SPEAKING' ? 4.8 : 3.4}
                  strokeOpacity={0.95}

                />
                {/* Incandescent white core of the merged trunk */}
                <line
                  x1={starCx}
                  y1={starCy}
                  x2={trunkExitX}
                  y2={trunkExitY}
                  stroke="#ffffff"
                  strokeWidth={1.8}
                  strokeOpacity={1.0}
                />
                {/* Central hot junction point inside the heart of the star */}
                <circle
                  cx={starCx}
                  cy={starCy}
                  r={3.2}
                  fill="#ffffff"

                />
              </g>

              {/* RENDER ALL 12 CONDUIT LINES:
                  All start at (starCx, starCy) inside the star, share the same tangent leaving it,
                  then fan out gracefully to each symbol circle!
              */}
              {functions.map((fn, idx) => {
                const targetY = 28 + idx * 45;
                const isRed = fn.color === 'red';
                const isHovered = hoveredId === fn.id;
                const isVoiceActive =
                  state === 'SPEAKING' &&
                  (fn.id === 'fn-03' || fn.id === 'fn-01');

                // Path originates INSIDE the star at (starCx, starCy)
                // Shares CP1 with the trunk exit, then branches smoothly towards each symbol
                const cp2X = lineTouchX - 54 - (idx % 2) * 8;
                const cp2Y = targetY;

                const pathD = `M ${starCx} ${starCy} C ${trunkExitX} ${trunkExitY}, ${cp2X} ${cp2Y}, ${lineTouchX} ${targetY}`;

                return (
                  <g
                    key={`line-${fn.id}`}
                    className="pointer-events-none"
                  >
                    {/* 1. Enhanced Luminous Outer Aura (Deixe as linhas mais brilhosas) */}
                    <path
                      d={pathD}
                      stroke={fn.pathColor}
                      strokeWidth={isHovered || isVoiceActive ? 2.8 : 1.6}
                      strokeOpacity={
                        isVoiceActive
                          ? 1.0
                          : isHovered
                          ? 0.98
                          : isRed
                          ? 0.88
                          : 0.82
                      }

                    />

                    {/* 2. Sharp vibrant optic fiber body */}
                    <path
                      d={pathD}
                      stroke={fn.pathColor}
                      strokeWidth={isHovered || isVoiceActive ? 1.2 : 0.85}
                      strokeOpacity={0.95}
                    />

                    {/* 3. Incandescent white-hot core hairline (increased brightness) */}
                    <path
                      d={pathD}
                      stroke={fn.coreColor}
                      strokeWidth={0.42}
                      strokeOpacity={0.98}
                    />

                    {/* 4. ANIMATED PHOTONIC DATA PACKET:
                        - Larger radius (2.8 - 3.6px)
                        - Brilliant electric blue/cyan (#00f0ff / #38bdf8)
                        - Highly luminous glow filter
                    */}
                    <circle
                      r={isVoiceActive ? 10.8 : 8.4}
                      fill="url(#packet-light)"
                    >
                      <animateMotion
                        path={pathD}
                        dur={`${1.6 + (idx % 4) * 0.28}s`}
                        repeatCount="indefinite"
                        begin={`${idx * 0.11}s`}
                      />
                    </circle>

                    {/* 4b. Pure white incandescent pupil inside the blue packet */}
                    <circle
                      r={isVoiceActive ? 1.6 : 1.2}
                      fill="#ffffff"
                    >
                      <animateMotion
                        path={pathD}
                        dur={`${1.6 + (idx % 4) * 0.28}s`}
                        repeatCount="indefinite"
                        begin={`${idx * 0.11}s`}
                      />
                    </circle>

                    {/* 5. Secondary trailing electric blue spark (larger & brighter) */}
                    <circle
                      r={5.1}
                      fill="url(#packet-light)"
                    >
                      <animateMotion
                        path={pathD}
                        dur={`${2.2 + (idx % 3) * 0.35}s`}
                        repeatCount="indefinite"
                        begin={`${idx * 0.15 + 0.7}s`}
                      />
                    </circle>

                    {/* PHYSICAL CONNECTION TERMINAL: Lit bead touching the symbol ring */}
                    <circle
                      cx={lineTouchX}
                      cy={targetY}
                      r={2.4}
                      fill="#00f0ff"
                      stroke="#ffffff"
                      strokeWidth={0.8}

                    />
                  </g>
                );
              })}

              {/* RENDER FLOATING SYMBOLS & LABELS (Pushed right against the right border) */}
              {functions.map((fn, idx) => {
                const targetY = 28 + idx * 45;
                const isRed = fn.color === 'red';
                const isHovered = hoveredId === fn.id;
                const isVoiceActive =
                  state === 'SPEAKING' &&
                  (fn.id === 'fn-03' || fn.id === 'fn-01');
                const Icon = fn.icon;

                return (
                  <g
                    key={`node-${fn.id}`}
                    className="cursor-pointer"
                    role="button" tabIndex={0} aria-label={fn.label}
                    onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onModuleClick?.(idx); } }}
                    onMouseEnter={() => setHoveredId(fn.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => {
                      onModuleClick?.(idx);
                    }}
                  >
                    {/* Glowing outer halo around symbol on hover or voice */}
                    {(isHovered || isVoiceActive) && (
                      <circle
                        cx={symbolX}
                        cy={targetY}
                        r={symbolRadius + 3.5}
                        fill="none"
                        stroke={isRed ? '#ff2255' : '#00f0ff'}
                        strokeWidth={1.0}
                        strokeOpacity={0.7}
                        className="animate-pulse"
                      />
                    )}

                    {/* Circular Symbol Ring - Directly connected to the line */}
                    <circle
                      cx={symbolX}
                      cy={targetY}
                      r={symbolRadius}
                      fill={
                        isRed
                          ? isVoiceActive
                            ? '#2b0712'
                            : '#140207'
                          : isVoiceActive
                          ? '#03203f'
                          : '#020f26'
                      }
                      stroke={
                        isRed
                          ? isVoiceActive
                            ? '#ff4477'
                            : isHovered
                            ? '#ff2255'
                            : '#e11d48'
                          : isVoiceActive
                          ? '#38bdf8'
                          : isHovered
                          ? '#00f0ff'
                          : '#0284c7'
                      }
                      strokeWidth={isHovered || isVoiceActive ? 1.4 : 1.0}

                    />

                    {/* Inner Icon embedded directly at the symbol center */}
                    <foreignObject
                      x={symbolX - 7}
                      y={targetY - 7}
                      width={14}
                      height={14}
                      className="pointer-events-none"
                    >
                      <div className="w-full h-full flex items-center justify-center">
                        <Icon
                          className={`w-3.5 h-3.5 ${
                            isRed
                              ? isVoiceActive
                                ? 'text-rose-200'
                                : isHovered
                                ? 'text-rose-200'
                                : 'text-rose-400'
                              : isVoiceActive
                              ? 'text-cyan-200'
                              : isHovered
                              ? 'text-cyan-200'
                              : 'text-cyan-300'
                          }`}
                        />
                      </div>
                    </foreignObject>

                    {/* Clean Floating Function Label Text:
                        Supports multi-line breaking for ENTENDIMENTO / DE LINGUAGEM as requested!
                    */}
                    {fn.lines ? (
                      <text
                        x={symbolX + 17}
                        y={targetY - 2.5}
                        fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                        fontSize="9.2"
                        fontWeight="600"
                        letterSpacing="0.08em"
                        fill={
                          isRed
                            ? isVoiceActive
                              ? '#ffe4e6'
                              : isHovered
                              ? '#fda4af'
                              : '#fb7185'
                            : isVoiceActive
                            ? '#e0f2fe'
                            : isHovered
                            ? '#bae6fd'
                            : '#cbd5e1'
                        }
                        filter="url(#textShadowGlow)"
                        className="select-none transition-colors duration-200"
                      >
                        <tspan x={symbolX + 17} dy="0">
                          {fn.lines[0]}
                        </tspan>
                        <tspan x={symbolX + 17} dy="11">
                          {fn.lines[1]}
                        </tspan>
                      </text>
                    ) : (
                      <text
                        x={symbolX + 17}
                        y={targetY + 3.5}
                        fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                        fontSize="9.5"
                        fontWeight="600"
                        letterSpacing="0.08em"
                        fill={
                          isRed
                            ? isVoiceActive
                              ? '#ffe4e6'
                              : isHovered
                              ? '#fda4af'
                              : '#fb7185'
                            : isVoiceActive
                            ? '#e0f2fe'
                            : isHovered
                            ? '#bae6fd'
                            : '#cbd5e1'
                        }
                        filter="url(#textShadowGlow)"
                        className="select-none transition-colors duration-200"
                      >
                        {fn.label}
                      </text>
                    )}

                    {/* Dynamic voice waveform if speech node */}
                    {fn.id === 'fn-03' && state === 'SPEAKING' && (
                      <foreignObject
                        x={symbolX + 17 + fn.label.length * 6.0 + 6}
                        y={targetY - 6}
                        width={24}
                        height={12}
                        className="pointer-events-none"
                      >
                        <div className="flex items-center gap-0.5 h-full">
                          <span className="w-0.5 h-2 bg-rose-400 rounded-full animate-pulse" />
                          <span className="w-0.5 h-3 bg-rose-300 rounded-full animate-bounce" />
                          <span className="w-0.5 h-1.5 bg-rose-400 rounded-full animate-pulse" />
                        </div>
                      </foreignObject>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
};

export const IntegratedNeuralStage=React.memo(Stage);
