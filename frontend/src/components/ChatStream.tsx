import React, { useState, useRef, useEffect } from 'react';
import { Send, ArrowRight } from 'lucide-react';
import type { Message, Artifact } from '../types';
import { MessageBubble } from './MessageBubble';

interface ChatStreamProps {
  messages: Message[];
  isGenerating: boolean;
  statusMessage: string | null;
  onSendMessage: (content: string) => void;
  onOpenArtifact: (artifact: Artifact) => void;
}

const CURATED_PROMPTS = [
  {
    tag: 'Tactical Growth',
    text: "What are Elena Verna's 10 growth tactics that never work?",
    description: 'Deconstructs why premature growth teams and rebrands fail.',
  },
  {
    tag: 'Product Strategy',
    text: 'How does Brian Chesky run product reviews and single roadmaps at Airbnb?',
    description: 'Being in the details vs micromanagement and managing by influence.',
  },
  {
    tag: 'Ship 30 Essay',
    text: 'Draft a Ship 30 for 30 essay on why performance marketing fails to create accumulating advantages.',
    description: 'Produces a ~1,250-word structured atomic essay with hooks and tactical pillars.',
  },
];

export const ChatStream: React.FC<ChatStreamProps> = ({
  messages,
  isGenerating,
  statusMessage,
  onSendMessage,
  onOpenArtifact,
}) => {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const userScrolledUpRef = useRef(false);

  const handleEditInInput = (text: string) => {
    setInput(text);
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(text.length, text.length);
      }
    }, 50);
  };

  const scrollToBottom = () => {
    if (!userScrolledUpRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, statusMessage]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 60;
    userScrolledUpRef.current = !isAtBottom;
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isGenerating) return;
    userScrolledUpRef.current = false;
    onSendMessage(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-pane">
      <div className="messages-scroll" ref={scrollRef} onScroll={handleScroll}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <h2 className="empty-state-title">Ask Lenny's Podcast Archive</h2>
            <p className="empty-state-subtitle">
              Grounded exclusively in 300+ real operator interviews. All answers cite verified
              YouTube timestamps. Select a topic below or ask your own question:
            </p>

            <div className="prompt-cards">
              {CURATED_PROMPTS.map((p, idx) => (
                <div
                  key={idx}
                  className="prompt-card"
                  onClick={() => onSendMessage(p.text)}
                  role="button"
                  tabIndex={0}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="prompt-tag">{p.tag}</span>
                    <ArrowRight size={13} color="var(--accent-primary)" />
                  </div>
                  <div className="prompt-text">{p.text}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <MessageBubble
              key={msg.id || idx}
              message={msg}
              onOpenArtifact={onOpenArtifact}
              onResend={onSendMessage}
              onEditInInput={handleEditInInput}
              disabled={isGenerating}
            />
          ))
        )}

        {/* Dynamic status line during generation */}
        {isGenerating && statusMessage && (
          <div className="status-indicator">
            <span className="pulse-dot" />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>

      <div className="input-container">
        <form className="input-box" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder="Ask a growth question or type 'Draft a Ship 30 essay on...'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isGenerating}
          />
          <div className="input-actions">
            <span className="input-hint">Enter to send · Shift+Enter for newline</span>
            <button
              type="submit"
              className="send-btn"
              disabled={isGenerating || !input.trim()}
            >
              <span>Send</span>
              <Send size={13} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
