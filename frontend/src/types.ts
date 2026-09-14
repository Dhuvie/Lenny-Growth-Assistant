export interface Citation {
  guest: string;
  episode_title: string;
  episode_slug: string;
  start_timestamp: string;
  start_seconds: number;
  youtube_url: string;
  snippet: string;
  similarity: number;
}

export interface Artifact {
  id: string;
  title: string;
  type: 'markdown' | 'html' | 'react';
  content: string;
  word_count: number;
  created_at?: string;
}

export interface Message {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: Citation[];
  artifacts?: Artifact[];
  model_provider?: string;
  created_at?: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  session_metadata?: Record<string, any>;
  message_count?: number;
  messages?: Message[];
}

export interface AppInfo {
  app_name: string;
  active_provider: string;
  active_model: string;
  embedding_model: string;
  providers_supported: string[];
  available_models?: Record<string, string[]>;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  database: string;
  llm_provider: {
    provider: string;
    model: string;
    status: string;
    latency_ms?: number;
    detail?: string;
  };
  indexed_episodes: number;
  indexed_chunks: number;
  timestamp: string;
}
