import React, { useState } from 'react';
import { FileText, ArrowRight, Sparkles, RotateCcw, Pencil, Copy, Check, Send } from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import type { Message, Artifact } from '../types';
import { CitationBadge } from './CitationBadge';

interface MessageBubbleProps {
  message: Message;
  onOpenArtifact?: (artifact: Artifact) => void;
  onResend?: (content: string) => void;
  onEditInInput?: (content: string) => void;
  disabled?: boolean;
}

function getDisplayContent(
  content: string,
  artifacts?: Artifact[]
): { text: string; isStreamingArtifact: boolean } {
  // If artifacts are present, strip the raw code/document from chat display
  if (artifacts && artifacts.length > 0) {
    let cleaned = content;

    // 1. Strip :::artifact{...} ... ::: blocks
    cleaned = cleaned.replace(/:::artifact\{[^}]*\}[\s\S]*?(?::::|$)/g, '');

    // 2. Strip ```html ... ``` blocks (complete or streaming)
    cleaned = cleaned.replace(/```(?:html|htm)[\s\S]*?(?:```|$)/gi, '');

    // 3. Strip ```tsx / jsx / react ... ``` blocks
    cleaned = cleaned.replace(/```(?:tsx|jsx|react)[\s\S]*?(?:```|$)/gi, '');

    // 4. Strip ```markdown ... ``` blocks if markdown artifact
    if (artifacts.some((a) => a.type === 'markdown')) {
      cleaned = cleaned.replace(/```(?:markdown|md)[\s\S]*?(?:```|$)/gi, '');
    }

    // 5. Strip exact artifact content if still present in raw message
    for (const art of artifacts) {
      if (art.content && cleaned.includes(art.content)) {
        cleaned = cleaned.replace(art.content, '');
      }
    }

    cleaned = cleaned.trim();
    if (!cleaned) {
      const art = artifacts[0];
      const typeLabel =
        art.type === 'html'
          ? 'HTML/CSS component'
          : art.type === 'react'
          ? 'interactive React web component'
          : 'document';
      return {
        text: `I have generated the ${typeLabel} below. You can view, preview, and test it in the Artifact Viewer:`,
        isStreamingArtifact: false,
      };
    }

    return { text: cleaned, isStreamingArtifact: false };
  }

  // If no artifact yet, check if code or artifact block is currently streaming
  const hasArtifactFence =
    content.includes('```html') ||
    content.includes('```htm') ||
    content.includes('```tsx') ||
    content.includes('```jsx') ||
    content.includes('```react') ||
    content.includes(':::artifact');

  if (hasArtifactFence) {
    const indices = [
      content.indexOf('```html'),
      content.indexOf('```htm'),
      content.indexOf('```tsx'),
      content.indexOf('```jsx'),
      content.indexOf('```react'),
      content.indexOf(':::artifact'),
    ].filter((i) => i !== -1);

    const splitIndex = Math.min(...indices);
    const prefix = content.slice(0, splitIndex).trim();

    return {
      text: prefix || 'Generating artifact for the Artifact Viewer...',
      isStreamingArtifact: true,
    };
  }

  return { text: content, isStreamingArtifact: false };
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onOpenArtifact,
  onResend,
  onEditInInput,
  disabled = false,
}) => {
  const isUser = message.role === 'user';
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveAndSend = () => {
    const trimmed = editText.trim();
    if (!trimmed || disabled) return;
    setIsEditing(false);
    onResend?.(trimmed);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditText(message.content);
  };

  const { text: displayMarkdown, isStreamingArtifact } = isUser
    ? { text: message.content, isStreamingArtifact: false }
    : getDisplayContent(message.content, message.artifacts);

  const renderedContent = isUser
    ? null
    : DOMPurify.sanitize(marked.parse(displayMarkdown) as string);

  return (
    <div className={`message-row ${message.role}`}>
      <div className="message-bubble">
        {isUser ? (
          isEditing ? (
            <div className="user-prompt-edit-card">
              <textarea
                className="user-prompt-edit-textarea"
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSaveAndSend();
                  } else if (e.key === 'Escape') {
                    handleCancel();
                  }
                }}
                rows={Math.min(6, Math.max(2, editText.split('\n').length))}
                autoFocus
              />
              <div className="user-prompt-edit-footer">
                <span className="user-prompt-edit-hint">Enter to send · Esc to cancel</span>
                <div className="user-prompt-edit-buttons">
                  <button
                    type="button"
                    className="user-prompt-cancel-btn"
                    onClick={handleCancel}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="user-prompt-send-btn"
                    onClick={handleSaveAndSend}
                    disabled={!editText.trim() || disabled}
                  >
                    <span>Send</span>
                    <Send size={11} />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div>{message.content}</div>
          )
        ) : (
          <>
            <div
              className="markdown-body"
              dangerouslySetInnerHTML={{ __html: renderedContent || '' }}
            />

            {/* Live indicator while artifact code is generating */}
            {isStreamingArtifact &&
              (!message.artifacts || message.artifacts.length === 0) && (
                <div className="artifact-callout streaming">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="pulse-dot" style={{ width: 8, height: 8 }} />
                    <span className="artifact-callout-title" style={{ fontSize: 13 }}>
                      Generating artifact in viewer...
                    </span>
                  </div>
                </div>
              )}
          </>
        )}

        {/* Footnote citations */}
        {message.sources && message.sources.length > 0 && (
          <div className="citations-container">
            <div className="citations-header">
              <Sparkles size={12} color="var(--accent-primary)" />
              Sources Cited from Podcast Transcripts ({message.sources.length})
            </div>
            <div className="citations-grid">
              {message.sources.map((cit, idx) => (
                <CitationBadge key={idx} citation={cit} />
              ))}
            </div>
          </div>
        )}

        {/* Embedded Artifact Callouts */}
        {message.artifacts && message.artifacts.length > 0 && onOpenArtifact && (
          <div style={{ marginTop: 12 }}>
            {message.artifacts.map((art) => (
              <div key={art.id} className="artifact-callout">
                <div className="artifact-callout-info">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <FileText size={14} color="var(--accent-primary)" />
                    <span className="artifact-callout-title">{art.title}</span>
                  </div>
                  <span className="artifact-callout-meta">
                    {art.type.toUpperCase()} · {art.word_count.toLocaleString()} words · Ready to review
                  </span>
                </div>
                <button
                  type="button"
                  className="artifact-open-btn"
                  onClick={() => onOpenArtifact(art)}
                >
                  <span>Open in Viewer</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action buttons below user prompt */}
      {isUser && !isEditing && (
        <div className="user-prompt-actions">
          <button
            type="button"
            className="prompt-action-btn"
            title="Edit this prompt inline"
            onClick={() => setIsEditing(true)}
            disabled={disabled}
          >
            <Pencil size={12} />
            <span>Edit</span>
          </button>
          {onEditInInput && (
            <button
              type="button"
              className="prompt-action-btn"
              title="Load prompt into input box below"
              onClick={() => onEditInInput(message.content)}
              disabled={disabled}
            >
              <span>Edit in Box</span>
            </button>
          )}
          <button
            type="button"
            className="prompt-action-btn resend"
            title="Resend this prompt"
            onClick={() => onResend?.(message.content)}
            disabled={disabled}
          >
            <RotateCcw size={12} />
            <span>Resend</span>
          </button>
          <button
            type="button"
            className="prompt-action-btn"
            title="Copy prompt"
            onClick={handleCopy}
          >
            {copied ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      )}
    </div>
  );
};
