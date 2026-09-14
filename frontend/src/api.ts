import type { Session, Citation, Artifact, AppInfo, HealthStatus } from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchAppInfo(): Promise<AppInfo> {
  const res = await fetch(`${API_BASE}/api/info`);
  if (!res.ok) throw new Error('Failed to fetch app configuration');
  return res.json();
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/api/sessions`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

export async function createSession(title?: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: title || 'New Growth Conversation' }),
  });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

export async function fetchSessionDetail(sessionId: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to fetch session ${sessionId}`);
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete session ${sessionId}`);
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onStatus: (message: string) => void;
  onCitations: (citations: Citation[]) => void;
  onArtifact: (artifact: Artifact) => void;
  onError: (error: string) => void;
  onDone: () => void;
}

export async function streamChatMessage(
  sessionId: string,
  content: string,
  callbacks: StreamCallbacks,
  options?: { provider?: string; model?: string }
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      session_id: sessionId,
      content,
      stream: true,
      provider: options?.provider,
      model: options?.model,
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    callbacks.onError(`Request failed (${res.status}): ${errText}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError('ReadableStream is not supported by this browser.');
    return;
  }

  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith('data: ')) continue;

      const dataStr = trimmed.slice(6);
      try {
        const event = JSON.parse(dataStr);
        if (event.type === 'token') {
          callbacks.onToken(event.token);
        } else if (event.type === 'status') {
          callbacks.onStatus(event.message);
        } else if (event.type === 'citations') {
          callbacks.onCitations(event.citations);
        } else if (event.type === 'artifact') {
          callbacks.onArtifact(event.artifact);
        } else if (event.type === 'error') {
          callbacks.onError(event.error);
        } else if (event.type === 'done') {
          callbacks.onDone();
        }
      } catch (e) {
        // Skip unparsable line
      }
    }
  }

  callbacks.onDone();
}
