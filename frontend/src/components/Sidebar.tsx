import React from 'react';
import { Plus, Trash2, MessageSquare } from 'lucide-react';
import type { Session, HealthStatus } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  health: HealthStatus | null;
  isOpen: boolean;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  health,
  isOpen,
  onSelectSession,
  onNewChat,
  onDeleteSession,
}) => {
  return (
    <aside className={`sidebar ${isOpen ? '' : 'collapsed'}`} aria-label="Conversation History">
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={15} />
          <span>New Chat</span>
        </button>
      </div>

      <div className="sessions-list">
        {sessions.length === 0 ? (
          <div style={{ padding: '16px 12px', fontSize: 12, color: 'var(--text-muted)' }}>
            No previous conversations.
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <div
                key={session.id}
                className={`session-item ${isActive ? 'active' : ''}`}
                onClick={() => onSelectSession(session.id)}
                role="button"
                tabIndex={0}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden', flex: 1 }}>
                  <MessageSquare size={13} style={{ opacity: isActive ? 1 : 0.5, flexShrink: 0 }} />
                  <span className="session-title">{session.title}</span>
                </div>
                <button
                  className="session-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(session.id);
                  }}
                  title="Delete conversation"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="sidebar-footer">
        <div className="corpus-stat">
          <span>Episodes Indexed:</span>
          <b>{health?.indexed_episodes ?? 20}</b>
        </div>
        <div className="corpus-stat">
          <span>Transcript Chunks:</span>
          <b>{health?.indexed_chunks?.toLocaleString() ?? '1,450'}</b>
        </div>
        <div className="corpus-stat">
          <span>Index Topology:</span>
          <b>HNSW · 384d</b>
        </div>
      </div>
    </aside>
  );
};
