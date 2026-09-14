import React from 'react';
import { PanelLeft, Cpu } from 'lucide-react';
import type { AppInfo, HealthStatus } from '../types';

interface HeaderProps {
  appInfo: AppInfo | null;
  health: HealthStatus | null;
  sidebarOpen: boolean;
  selectedProvider: string;
  selectedModel: string;
  onModelChange: (provider: string, model: string) => void;
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  appInfo,
  health,
  sidebarOpen,
  selectedProvider,
  selectedModel,
  onModelChange,
  onToggleSidebar,
}) => {
  const isHealthy = health?.status === 'healthy';
  const isDegraded = health?.status === 'degraded';
  const dotClass = isHealthy ? 'healthy' : isDegraded ? 'degraded' : 'unhealthy';

  const currentValue = `${selectedProvider}|${selectedModel}`;

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const [p, m] = e.target.value.split('|');
    if (p && m) {
      onModelChange(p, m);
    }
  };

  return (
    <header className="app-header">
      <div className="brand-section">
        <button
          className="icon-btn"
          onClick={onToggleSidebar}
          title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-label="Toggle sidebar"
        >
          <PanelLeft size={18} />
        </button>

        <h1 className="brand-title" title={appInfo?.app_name || 'The Lenny Growth Assistant'}>
          <span>The Lenny Growth Assistant</span>
          <span className="brand-badge">Archive</span>
        </h1>
      </div>

      <div className="header-status">
        {/* Interactive Model Selector */}
        <div
          className="model-badge"
          title={`Active model: ${selectedModel} via ${selectedProvider.toUpperCase()}`}
        >
          <Cpu size={12} color="var(--accent-primary)" />
          <span style={{ opacity: 0.7 }}>Engine:</span>
          <select
            className="model-select"
            value={currentValue}
            onChange={handleSelectChange}
            aria-label="Select AI Model Provider"
          >
            <optgroup label="Local (Zero Cloud Keys)">
              <option value="ollama|llama3.1:8b">Ollama: llama3.1:8b</option>
            </optgroup>
            <optgroup label="Google Gemini Cloud">
              <option value="gemini|gemini-3.5-flash-lite">Gemini: 3.5 Flash Lite (Fastest)</option>
              <option value="gemini|gemini-3.8-flash">Gemini: 3.8 Flash (State of Art)</option>
              <option value="gemini|gemini-3.7-flash">Gemini: 3.7 Flash (Hybrid Reasoning)</option>
              <option value="gemini|gemini-2.5-flash">Gemini: 2.5 Flash (Efficient)</option>
              <option value="gemini|gemini-2.5-pro">Gemini: 2.5 Pro (Deep Reasoning)</option>
              <option value="gemini|gemini-2.0-flash">Gemini: 2.0 Flash (Stable)</option>
            </optgroup>
            <optgroup label="Anthropic Claude">
              <option value="claude|claude-3-5-sonnet-20241022">Claude: 3.5 Sonnet</option>
            </optgroup>
            <optgroup label="OpenAI">
              <option value="openai|gpt-4o">OpenAI: GPT-4o</option>
            </optgroup>
          </select>
        </div>

        {/* Live Health Status Pill */}
        <div
          className="health-pill"
          title={`Status: ${health?.status || 'checking...'}\nDatabase: ${health?.database || 'unknown'}\nProvider: ${health?.llm_provider?.status || 'unknown'}`}
        >
          <span className={`health-dot ${dotClass}`} />
          <span>
            {isHealthy ? 'Operational' : isDegraded ? 'Degraded' : 'Offline'}
          </span>
        </div>
      </div>
    </header>
  );
};
