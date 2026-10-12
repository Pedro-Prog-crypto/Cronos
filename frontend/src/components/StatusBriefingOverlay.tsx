import React from 'react';
import { ShieldCheck, Sparkles, Filter, Newspaper } from 'lucide-react';

interface StatusBriefingOverlayProps {
  statusText?: string;
  subText?: string;
  categoryTags?: string[];
  type?: 'initial' | 'filtering' | 'news_radar';
}

export const StatusBriefingOverlay: React.FC<StatusBriefingOverlayProps> = ({
  statusText = 'PASSAGEM PADRÃO',
  subText = 'Sem desvios relevantes. Dados consolidados desde ontem',
  categoryTags = ['AGENDA', 'E-MAILS', 'NOTÍCIAS', 'CLIMA', 'PRIORIDADES'],
  type = 'initial',
}) => {
  return (
    <div className="relative z-20 w-full max-w-[480px] mx-auto p-4 rounded-xl bg-[#030d22]/85 backdrop-blur-md border border-cyan-500/30 shadow-[0_0_25px_rgba(0,180,255,0.2)] text-center animate-in fade-in zoom-in-95 duration-500">
      <div className="flex items-center justify-center gap-2 mb-2 text-xs font-mono tracking-widest text-cyan-300 uppercase">
        {type === 'filtering' ? (
          <Filter className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
        ) : type === 'news_radar' ? (
          <Newspaper className="w-3.5 h-3.5 text-cyan-400" />
        ) : (
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
        )}
        <span>{statusText}</span>
      </div>

      <div className="text-base sm:text-lg font-bold text-white tracking-tight leading-snug">
        {subText}
      </div>

      {categoryTags && categoryTags.length > 0 && (
        <div className="flex items-center justify-center gap-1.5 flex-wrap mt-3 pt-2.5 border-t border-blue-900/40">
          {categoryTags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] font-mono tracking-wider px-2 py-0.5 rounded bg-blue-950/60 border border-blue-500/25 text-blue-200/80"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
