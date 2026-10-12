import React from 'react';

interface CronosLogoProps {
  className?: string;
  isSpeaking?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export const CronosLogo: React.FC<CronosLogoProps> = ({
  className = '',
  isSpeaking = false,
  size = 'lg',
}) => {
  const sizeClasses = {
    xs: 'w-[210px] h-[35px]',
    sm: 'w-[250px] h-[42px]',
    md: 'w-[320px] h-[54px]',
    lg: 'w-[420px] h-[70px]',
    xl: 'w-[520px] h-[88px]',
  };

  return (
    <div
      className={`relative flex items-center justify-center select-none transition-all duration-500 ${sizeClasses[size]} ${className}`}
      style={{
        filter: isSpeaking
          ? 'drop-shadow(0 0 6px #00f0ff) drop-shadow(0 0 16px #0088ff) drop-shadow(0 0 32px rgba(0, 180, 255, 0.9))'
          : 'drop-shadow(0 0 4px #00e5ff) drop-shadow(0 0 12px #0077ff) drop-shadow(0 0 22px rgba(0, 140, 255, 0.65))',
      }}
    >
      <svg
        viewBox="0 0 560 90"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full overflow-visible"
      >
        <defs>
          {/* Luminous Neon Electric Blue Gradient */}
          <linearGradient id="neonCyanBlue" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#d5f8ff" />
            <stop offset="45%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#00e5ff" />
          </linearGradient>

          {/* Core high-intensity glow filter */}
          <filter id="cronosGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="1.5" result="blur1" />
            <feGaussianBlur stdDeviation="4.0" result="blur2" />
            <feMerge>
              <feMergeNode in="blur2" />
              <feMergeNode in="blur1" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g
          stroke="url(#neonCyanBlue)"
          strokeWidth="2.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter="url(#cronosGlow)"
        >
          {/* C: Geometric open circular arc */}
          <path
            d="M 74 24
               A 31 31 0 1 0 74 66"
            fill="none"
          />

          {/* R: Straight stem + upper rounded bowl + diagonal leg */}
          <line x1="126" y1="14" x2="126" y2="76" />
          <path
            d="M 126 14
               H 154
               A 17 17 0 0 1 154 48
               H 126"
            fill="none"
          />
          <line x1="150" y1="48" x2="174" y2="76" />

          {/* FIRST O: ICONIC CONCENTRIC IRIS & GLOWING PUPIL TARGET */}
          {/* Outer circle */}
          <circle cx="236" cy="45" r="31" fill="none" />
          {/* Concentric inner circle */}
          <circle
            cx="236"
            cy="45"
            r="16"
            strokeWidth="1.8"
            stroke="#38bdf8"
            strokeOpacity="0.8"
            fill="none"
          />
          {/* Central glowing pupil dot */}
          <circle
            cx="236"
            cy="45"
            r="4.5"
            fill="#ffffff"
            stroke="#e0ffff"
            strokeWidth="0.8"
          />

          {/* N: Symmetrical upright stems and clean diagonal */}
          <line x1="304" y1="14" x2="304" y2="76" />
          <line x1="304" y1="14" x2="352" y2="76" />
          <line x1="352" y1="14" x2="352" y2="76" />

          {/* SECOND O: Clean open circle */}
          <circle cx="420" cy="45" r="31" fill="none" />

          {/* S: Pure geometric modern S with balanced curves */}
          <path
            d="M 504 26
               C 504 15, 470 14, 470 28
               C 470 42, 504 44, 504 62
               C 504 78, 470 77, 470 64"
            fill="none"
          />
        </g>
      </svg>
    </div>
  );
};
