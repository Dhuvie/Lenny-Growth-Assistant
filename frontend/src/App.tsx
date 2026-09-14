import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatStream } from './components/ChatStream';
import { ArtifactViewer } from './components/ArtifactViewer';
import {
  fetchAppInfo,
  fetchHealth,
  fetchSessions,
  createSession,
  fetchSessionDetail,
  deleteSession as apiDeleteSession,
  streamChatMessage,
} from './api';
import type { Session, Message, Artifact, AppInfo, HealthStatus, Citation } from './types';

export const App: React.FC = () => {
  const [appInfo, setAppInfo] = useState<AppInfo | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedProvider, setSelectedProvider] = useState<string>('ollama');
  const [selectedModel, setSelectedModel] = useState<string>('llama3.1:8b');

  // Poll health and app info
  const loadSystemStatus = useCallback(async () => {
    try {
      const [info, h] = await Promise.all([fetchAppInfo(), fetchHealth()]);
      setAppInfo(info);
      setHealth(h);
      if (info.active_provider) {
        setSelectedProvider((prev) => prev === 'ollama' ? info.active_provider : prev);
      }
      if (info.active_model) {
        setSelectedModel((prev) => prev === 'llama3.1:8b' ? info.active_model : prev);
      }
    } catch (e) {
      console.warn('Health check probe warning:', e);
    }
  }, []);

  useEffect(() => {
    loadSystemStatus();
    const interval = setInterval(loadSystemStatus, 30000);
    return () => clearInterval(interval);
  }, [loadSystemStatus]);

  // Load sessions on mount
  const loadSessions = useCallback(async () => {
    try {
      const list = await fetchSessions();
      setSessions(list);
      if (list.length > 0 && !activeSessionId) {
        setActiveSessionId(list[0].id);
        const detail = await fetchSessionDetail(list[0].id);
        setMessages(detail.messages || []);
      } else if (list.length === 0) {
        const newSess = await createSession('New Growth Conversation');
        setSessions([newSess]);
        setActiveSessionId(newSess.id);
        setMessages([]);
      }
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
  }, [activeSessionId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Switch session
  const handleSelectSession = async (sessionId: string) => {
    if (sessionId === activeSessionId || isGenerating) return;
    try {
      setActiveSessionId(sessionId);
      const detail = await fetchSessionDetail(sessionId);
      setMessages(detail.messages || []);
      setActiveArtifact(null);
    } catch (e) {
      console.error('Failed to switch session:', e);
    }
  };

  // Start New Chat
  const handleNewChat = async () => {
    if (isGenerating) return;
    try {
      const newSess = await createSession('New Growth Conversation');
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      setMessages([]);
      setActiveArtifact(null);
    } catch (e) {
      console.error('Failed to create new chat:', e);
    }
  };

  // Delete session
  const handleDeleteSession = async (sessionId: string) => {
    try {
      await apiDeleteSession(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);
      if (activeSessionId === sessionId) {
        if (remaining.length > 0) {
          handleSelectSession(remaining[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (e) {
      console.error('Failed to delete session:', e);
    }
  };

  // Send message and handle streaming
  const handleSendMessage = async (content: string) => {
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      const newSess = await createSession(content.slice(0, 30));
      setSessions((prev) => [newSess, ...prev]);
      currentSessionId = newSess.id;
      setActiveSessionId(currentSessionId);
    }

    const userMsg: Message = {
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsGenerating(true);
    setStatusMessage('Searching transcript archive...');

    let assistantContent = '';
    let currentCitations: Citation[] = [];
    let currentArtifacts: Artifact[] = [];

    setMessages((prev) => [
      ...prev,
      {
        role: 'assistant',
        content: '',
        sources: [],
        artifacts: [],
        model_provider: selectedProvider,
        created_at: new Date().toISOString(),
      },
    ]);

    await streamChatMessage(
      currentSessionId,
      content,
      {
        onToken: (token: string) => {
          assistantContent += token;
          setMessages((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                content: assistantContent,
              };
            }
            return next;
          });
        },
        onStatus: (msg: string) => {
          setStatusMessage(msg);
        },
        onCitations: (cits: Citation[]) => {
          currentCitations = cits;
          setMessages((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                sources: currentCitations,
              };
            }
            return next;
          });
        },
        onArtifact: (art: Artifact) => {
          currentArtifacts = [...currentArtifacts, art];
          setActiveArtifact(art);
          setMessages((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                artifacts: currentArtifacts,
              };
            }
            return next;
          });
        },
        onError: (errMsg: string) => {
          setMessages((prev) => {
            const next = [...prev];
            const lastIdx = next.length - 1;
            if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                content: `Error: ${errMsg}`,
              };
            }
            return next;
          });
          setIsGenerating(false);
          setStatusMessage(null);
        },
        onDone: () => {
          setIsGenerating(false);
          setStatusMessage(null);
          fetchSessions().then(setSessions).catch(console.warn);
        },
      },
      { provider: selectedProvider, model: selectedModel }
    );
  };

  return (
    <div className="app-container">
      <Header
        appInfo={appInfo}
        health={health}
        sidebarOpen={sidebarOpen}
        selectedProvider={selectedProvider}
        selectedModel={selectedModel}
        onModelChange={(p, m) => {
          setSelectedProvider(p);
          setSelectedModel(m);
        }}
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
      />

      <div className="main-layout">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          health={health}
          isOpen={sidebarOpen}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          onDeleteSession={handleDeleteSession}
        />

        <ChatStream
          messages={messages}
          isGenerating={isGenerating}
          statusMessage={statusMessage}
          onSendMessage={handleSendMessage}
          onOpenArtifact={(art) => setActiveArtifact(art)}
        />

        {activeArtifact && (
          <ArtifactViewer
            artifact={activeArtifact}
            onClose={() => setActiveArtifact(null)}
          />
        )}
      </div>
    </div>
  );
};

export default App;
