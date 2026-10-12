import React from 'react';
import {
  Sun,
  CloudRain,
  Wind,
  Calendar,
  CheckCircle2,
  Mail,
  AlertCircle,
  Clock,
  Sparkles,
  HeartPulse,
  ExternalLink,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';
import { CronosCard } from '../types/cronos';

interface PrimaryCardProps {
  card: CronosCard;
  onNext?: () => void;
  onDismiss?: () => void;
  isSpeaking?: boolean;
}

export const PrimaryCard: React.FC<PrimaryCardProps> = ({
  card,
  onNext,
  onDismiss,
  isSpeaking = false,
}) => {
  return (
    <div
      className={`relative w-full max-w-[560px] mx-auto rounded-2xl bg-[#030d22]/88 backdrop-blur-xl border border-cyan-500/35 shadow-[0_0_35px_rgba(0,180,255,0.22)] transition-all duration-500 overflow-hidden text-slate-100 ${
        isSpeaking ? 'ring-1 ring-cyan-400/40 shadow-[0_0_45px_rgba(0,229,255,0.3)]' : ''
      }`}
    >
      {/* Top luminous accent line */}
      <div className="absolute top-0 inset-x-0 h-[1.5px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent" />

      {/* Header bar */}
      <div className="flex items-center justify-between px-5 pt-4 pb-2.5 border-b border-blue-900/40 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#00e5ff]" />
          <span className="font-mono tracking-[0.16em] uppercase text-cyan-300/90 font-medium">
            {card.headerTag}
          </span>
        </div>
        <div className="flex items-center gap-2 text-slate-400 font-mono text-[11px]">
          {card.subtitle && (
            <span className="text-blue-300/70 truncate max-w-[200px]">
              {card.subtitle}
            </span>
          )}
        </div>
      </div>

      {/* Content body based on category */}
      <div className="p-5">
        {/* WEATHER CARD */}
        {card.categoryType === 'weather' && card.weatherData && (
          <div className="space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                  <Sun className="w-6 h-6 text-amber-400 animate-pulse" />
                  {card.weatherData.city}
                </h3>
                <p className="text-xs text-blue-200/75 mt-0.5">
                  {card.weatherData.condition} · Sensação {card.weatherData.feelsLike}°
                </p>
              </div>

              <div className="text-right">
                <div className="text-4xl font-extrabold tracking-tighter text-cyan-300 font-mono tabular-nums">
                  {card.weatherData.temp}°
                </div>
                <div className="text-[11px] text-blue-300/60 font-mono mt-0.5">
                  MÍN {card.weatherData.minTemp}° · MÁX {card.weatherData.maxTemp}°
                </div>
              </div>
            </div>

            {/* Weather Metrics row */}
            <div className="grid grid-cols-3 gap-2.5 pt-2 border-t border-blue-900/30 text-xs">
              <div className="p-2.5 rounded-xl bg-[#051433]/70 border border-blue-500/20 flex items-center gap-2.5">
                <CloudRain className="w-4 h-4 text-sky-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-blue-300/60 font-mono">CHUVA</div>
                  <div className="font-semibold text-sky-200 font-mono tabular-nums">
                    {card.weatherData.rainChance}%
                  </div>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-[#051433]/70 border border-blue-500/20 flex items-center gap-2.5">
                <Wind className="w-4 h-4 text-cyan-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-blue-300/60 font-mono">VENTO</div>
                  <div className="font-semibold text-cyan-200 font-mono tabular-nums">
                    {card.weatherData.windSpeed} km/h
                  </div>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-[#051433]/70 border border-blue-500/20 flex items-center gap-2.5">
                <Sun className="w-4 h-4 text-amber-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-blue-300/60 font-mono">ÍNDICE UV</div>
                  <div className="font-semibold text-amber-200 font-mono tabular-nums">
                    {card.weatherData.uvIndex || 7} (Alto)
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* AGENDA CARD */}
        {card.categoryType === 'agenda' && card.agendaData && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-300">
                  <Calendar className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white tracking-tight">
                    {card.agendaData.statusText}
                  </h3>
                  <p className="text-xs text-blue-300/70 mt-0.5">
                    {card.agendaData.description}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-[11px] font-mono text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>SINCRONIZADO</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[#051433]/60 border border-blue-500/20 text-xs text-blue-200/80 flex items-center justify-between">
              <span>Google Calendar & Workspace</span>
              <span className="font-mono text-[11px] text-cyan-300/80">0 eventos previstos hoje</span>
            </div>
          </div>
        )}

        {/* EMAILS CARD */}
        {card.categoryType === 'emails' && card.emailsData && (
          <div className="space-y-3.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-cyan-300">
                  <Mail className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white tracking-tight">
                    {card.title}
                  </h3>
                  <p className="text-xs text-blue-300/70">
                    {card.emailsData.priorityCount} mensagens de ação · {card.emailsData.unreadCount} na caixa
                  </p>
                </div>
              </div>

              <span className="text-[10px] font-mono tracking-wider px-2.5 py-1 rounded-md bg-amber-500/15 border border-amber-500/30 text-amber-300">
                AÇÃO REQUERIDA
              </span>
            </div>

            {/* Email list */}
            <div className="space-y-2 pt-1 max-h-[175px] overflow-y-auto pr-1 custom-scrollbar">
              {card.emailsData.items.map((item) => (
                <div
                  key={item.id}
                  className="p-2.5 rounded-xl bg-[#051433]/70 border border-blue-500/20 hover:border-cyan-500/40 transition-colors text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-cyan-200">
                      {item.sender}
                    </span>
                    {item.deadline && (
                      <span className="text-[10px] font-mono text-amber-300/90 flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" />
                        {item.deadline}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-blue-100/80 leading-relaxed line-clamp-2">
                    {item.subject}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* NEWS CARD */}
        {card.categoryType === 'news' && card.newsData && (
          <div className="space-y-3">
            <div className="flex gap-4">
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-500/15 border border-cyan-500/30 text-cyan-300">
                    {card.newsData.category}
                  </span>
                  <span className="text-[11px] text-blue-300/60 font-mono">
                    {card.newsData.source}
                  </span>
                </div>

                <h3 className="text-base font-semibold text-white leading-snug line-clamp-3">
                  {card.newsData.title}
                </h3>

                {card.newsData.summary && (
                  <p className="text-xs text-blue-200/70 leading-relaxed line-clamp-2">
                    {card.newsData.summary}
                  </p>
                )}
              </div>

              {card.newsData.thumbnailUrl && (
                <div className="w-36 h-24 rounded-xl overflow-hidden shrink-0 border border-cyan-500/25 shadow-md relative bg-slate-900">
                  <img
                    src={card.newsData.thumbnailUrl}
                    alt={card.newsData.title}
                    referrerPolicy="no-referrer"
                    className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#020718]/80 via-transparent to-transparent" />
                </div>
              )}
            </div>
          </div>
        )}

        {/* HEALTH CARD */}
        {card.categoryType === 'health' && card.healthData && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-pink-500/15 border border-pink-500/30 flex items-center justify-center text-pink-300">
                  <HeartPulse className="w-5 h-5 animate-pulse" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white tracking-tight">
                    {card.healthData.statusText}
                  </h3>
                  <p className="text-xs text-blue-300/70">
                    {card.healthData.observationsCount} observações registradas
                  </p>
                </div>
              </div>

              <span className="text-[10px] font-mono px-2.5 py-1 rounded bg-cyan-500/15 border border-cyan-500/30 text-cyan-300">
                STATUS ÓTIMO
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-[#051433]/70 border border-blue-500/20 text-center">
                <div className="text-[10px] text-blue-300/60 font-mono">SONO</div>
                <div className="text-sm font-bold text-cyan-300 font-mono mt-0.5">
                  {card.healthData.metrics.sleepScore}/100
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#051433]/70 border border-blue-500/20 text-center">
                <div className="text-[10px] text-blue-300/60 font-mono">FC REPOUSO</div>
                <div className="text-sm font-bold text-pink-300 font-mono mt-0.5">
                  {card.healthData.metrics.heartRateAvg} bpm
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-[#051433]/70 border border-blue-500/20 text-center">
                <div className="text-[10px] text-blue-300/60 font-mono">RECUPERAÇÃO</div>
                <div className="text-sm font-bold text-emerald-300 font-mono mt-0.5">
                  {card.healthData.metrics.recoveryState}
                </div>
              </div>
            </div>

            <p className="text-xs text-blue-200/80 italic text-center pt-1 border-t border-blue-900/30">
              "{card.healthData.promptQuestion}"
            </p>
          </div>
        )}
      </div>

      {/* Footer narration quote & controls */}
      <div className="px-5 py-3 bg-[#020817]/70 border-t border-blue-900/40 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-blue-300/75 truncate pr-2">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span className="truncate italic text-[11px]">
            {card.narrationText}
          </span>
        </div>

        {onNext && (
          <button
            onClick={onNext}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-200 hover:text-white transition-colors text-[11px] font-medium shrink-0 cursor-pointer"
          >
            <span>Próximo</span>
            <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
};
