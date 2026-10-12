import React from 'react';
import {
  Sun,
  Calendar,
  Mail,
  Newspaper,
  HeartPulse,
  Sparkles,
} from 'lucide-react';
import { CronosCard } from '../types/cronos';

interface SecondaryCardProps {
  card: CronosCard;
  onClick: () => void;
  isActive?: boolean;
}

export const SecondaryCard: React.FC<SecondaryCardProps> = ({
  card,
  onClick,
  isActive = false,
}) => {
  const getIcon = () => {
    switch (card.categoryType) {
      case 'weather':
        return <Sun className="w-3.5 h-3.5 text-amber-400" />;
      case 'agenda':
        return <Calendar className="w-3.5 h-3.5 text-cyan-400" />;
      case 'emails':
        return <Mail className="w-3.5 h-3.5 text-blue-400" />;
      case 'news':
        return <Newspaper className="w-3.5 h-3.5 text-sky-400" />;
      case 'health':
        return <HeartPulse className="w-3.5 h-3.5 text-pink-400" />;
      default:
        return <Sparkles className="w-3.5 h-3.5 text-cyan-400" />;
    }
  };

  const getPreviewText = () => {
    if (card.categoryType === 'weather' && card.weatherData) {
      return `${card.weatherData.temp}° · ${card.weatherData.condition}`;
    }
    if (card.categoryType === 'agenda' && card.agendaData) {
      return card.agendaData.statusText;
    }
    if (card.categoryType === 'emails' && card.emailsData) {
      return `${card.emailsData.priorityCount} pendentes`;
    }
    if (card.categoryType === 'news' && card.newsData) {
      return card.newsData.source;
    }
    if (card.categoryType === 'health' && card.healthData) {
      return `${card.healthData.observationsCount} observações`;
    }
    return card.title;
  };

  return (
    <button
      onClick={onClick}
      className={`group relative text-left w-full sm:w-[155px] md:w-[170px] p-2.5 rounded-xl bg-[#040f26]/85 backdrop-blur-md border transition-all duration-300 cursor-pointer overflow-hidden ${
        isActive
          ? 'border-cyan-400/80 shadow-[0_0_20px_rgba(0,229,255,0.35)] scale-105 bg-[#06183d]'
          : 'border-blue-500/25 hover:border-cyan-400/50 hover:bg-[#06173a]/90 hover:shadow-[0_0_15px_rgba(0,180,255,0.2)]'
      }`}
      title={`Abrir card: ${card.title}`}
    >
      {/* Subtle hover gradient glow */}
      <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/0 via-blue-500/5 to-cyan-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />

      {/* Card Header row */}
      <div className="flex items-center justify-between gap-1 mb-1.5 relative z-10">
        <div className="flex items-center gap-1.5 min-w-0">
          <div className="p-1 rounded-md bg-[#07193d] border border-blue-400/20 shrink-0">
            {getIcon()}
          </div>
          <span className="text-[10px] font-mono tracking-wider text-cyan-300/80 uppercase truncate">
            {card.categoryType}
          </span>
        </div>

        {card.categoryType === 'weather' && card.weatherData && (
          <span className="text-xs font-mono font-bold text-white tabular-nums">
            {card.weatherData.temp}°
          </span>
        )}
      </div>

      {/* Card Title */}
      <div className="relative z-10">
        <div className="text-xs font-semibold text-slate-100 truncate group-hover:text-cyan-200 transition-colors">
          {card.title}
        </div>
        <div className="text-[10px] text-blue-300/60 font-mono truncate mt-0.5">
          {getPreviewText()}
        </div>
      </div>
    </button>
  );
};
