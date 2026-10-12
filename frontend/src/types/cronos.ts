export type CronosState = 'IDLE' | 'LISTENING' | 'SPEAKING';

export type CardCategory = 'weather' | 'agenda' | 'emails' | 'news' | 'health' | 'status';

export interface WeatherData {
  city: string;
  region: string;
  temp: number;
  condition: string;
  minTemp: number;
  maxTemp: number;
  feelsLike: number;
  rainChance: number;
  windSpeed: number;
  uvIndex?: number;
}

export interface AgendaData {
  statusText: string;
  description: string;
  nextAppointment?: string;
  isSynced: boolean;
}

export interface EmailItem {
  id: string;
  sender: string;
  tag: string;
  subject: string;
  urgency: 'high' | 'medium' | 'normal';
  deadline?: string;
}

export interface EmailsData {
  unreadCount: number;
  priorityCount: number;
  items: EmailItem[];
}

export interface NewsData {
  category: string;
  title: string;
  summary?: string;
  source: string;
  thumbnailUrl: string;
  date?: string;
}

export interface HealthData {
  observationsCount: number;
  statusText: string;
  promptQuestion: string;
  metrics: {
    sleepScore: number;
    heartRateAvg: number;
    recoveryState: string;
  };
}

export interface StatusBriefingData {
  passagem: string;
  observacao: string;
  tags: string[];
}

export interface CronosCard {
  id: string;
  categoryType: CardCategory;
  headerTag: string;
  title: string;
  subtitle?: string;
  narrationText: string;
  weatherData?: WeatherData;
  agendaData?: AgendaData;
  emailsData?: EmailsData;
  newsData?: NewsData;
  healthData?: HealthData;
  statusData?: StatusBriefingData;
}

export interface BriefingStep {
  id: string;
  cardId?: string;
  spokenNarration: string;
  stageName: string;
  card?: CronosCard;
}
