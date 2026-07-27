export type QuestionKey =
  | "talents"
  | "direction"
  | "work"
  | "money"
  | "character"
  | "relationships"
  | "energy"
  | "custom";

export type DemoMode = "LIVE" | "DEMO FALLBACK" | string;

export interface TelegramWebApp {
  initData?: string;
  ready: () => void;
  expand: () => void;
  close?: () => void;
  MainButton?: {
    text: string;
    show: () => void;
    hide: () => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
  };
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

export interface AuthResponse {
  accessToken: string;
  demoMode?: DemoMode;
}

export interface LocationSuggestion {
  id: string;
  label: string;
  name?: string;
  country?: string;
  region?: string;
  timezone?: string;
  latitude?: number;
  longitude?: number;
}

export interface BirthFormData {
  name: string;
  birthDate: string;
  birthTime: string;
  locationQuery: string;
  location: LocationSuggestion | null;
}

export interface BodygraphRequest {
  name: string;
  birthDate: string;
  birthTime: string;
  location: {
    name: string;
    region?: string | null;
    country: string;
    timezone: string;
    latitude: number;
    longitude: number;
  };
}

export interface BodygraphResponse {
  sessionId: string;
  name: string;
  timezone: string;
  title?: string;
  summary: string;
  type: string;
  strategy: string;
  authority: string;
  profile: string;
  definition: string;
  lifeWork: string;
  demoMode?: DemoMode;
  details?: Record<string, string | string[] | null | undefined>;
}

export interface QuestionAnswer {
  questionType: QuestionKey;
  question?: string;
  title?: string;
  shortAnswer: string;
  manifestations: string[];
  strength: string;
  attentionPoint: string;
  basedOn: string[];
  reflectionQuestion: string;
}

export type Screen =
  | "welcome"
  | "form"
  | "confirm"
  | "calculating"
  | "result"
  | "answer"
  | "expired"
  | "authError";

export interface AppError {
  title: string;
  message: string;
  canRetry?: boolean;
}
