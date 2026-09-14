import React, { useState } from 'react';
import { X, Copy, Check, Eye, Code2 } from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import type { Artifact } from '../types';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  onClose: () => void;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ artifact, onClose }) => {
  const [viewMode, setViewMode] = useState<'rendered' | 'raw'>('rendered');
  const [copied, setCopied] = useState(false);

  if (!artifact) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const buildSandboxedHtml = (content: string) => {
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline' https:; script-src 'unsafe-inline' https:; font-src https: data:; img-src data: https:;">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 28px;
      line-height: 1.6;
      color: #1f2937;
      background-color: #ffffff;
      margin: 0;
    }
    h1, h2, h3, h4 { color: #111827; line-height: 1.3; }
    h1 { font-size: 24px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 0; }
    h2 { font-size: 18px; margin-top: 24px; }
    h3 { font-size: 15px; margin-top: 18px; }
    p { margin: 12px 0; }
    ul, ol { padding-left: 20px; margin: 12px 0; }
    li { margin-bottom: 6px; }
    blockquote {
      border-left: 4px solid #f59e0b;
      margin: 16px 0;
      padding-left: 14px;
      color: #4b5563;
      font-style: italic;
    }
    code {
      font-family: "JetBrains Mono", Consolas, monospace;
      font-size: 13px;
      background: #f3f4f6;
      padding: 2px 6px;
      border-radius: 4px;
    }
    pre {
      background: #111827;
      color: #f3f4f6;
      padding: 14px;
      border-radius: 6px;
      overflow-x: auto;
    }
    pre code { background: none; color: inherit; padding: 0; }
  </style>
</head>
<body>
  ${content}
</body>
</html>`;
  };

  const buildSandboxedReact = (code: string) => {
    // 1. Clean module imports so browser Babel can execute UMD React
    let processed = code
      .replace(/import\s+React\s*,\s*\{([^}]+)\}\s+from\s+['"]react['"];?/g, 'const {$1} = React;')
      .replace(/import\s+\{([^}]+)\}\s+from\s+['"]react['"];?/g, 'const {$1} = React;')
      .replace(/import\s+React\s+from\s+['"]react['"];?/g, '')
      .replace(/import\s+.*?from\s+['"]lucide-react['"];?/g, '')
      .replace(/import\s+.*?from\s+['"][^'"]+['"];?/g, '');

    // 2. Identify the main component to mount
    let componentName = 'App';
    const exportFuncMatch = processed.match(/export\s+default\s+function\s+([A-Za-z0-9_]+)/);
    if (exportFuncMatch) {
      componentName = exportFuncMatch[1];
      processed = processed.replace(/export\s+default\s+function/, 'function');
    } else {
      const exportVarMatch = processed.match(/export\s+default\s+([A-Za-z0-9_]+);?/);
      if (exportVarMatch) {
        componentName = exportVarMatch[1];
        processed = processed.replace(exportVarMatch[0], '');
      } else {
        const funcMatch = processed.match(/function\s+([A-Z][A-Za-z0-9_]*)/);
        if (funcMatch) {
          componentName = funcMatch[1];
        } else {
          const constMatch = processed.match(/(?:const|let)\s+([A-Z][A-Za-z0-9_]*)\s*=/);
          if (constMatch) {
            componentName = constMatch[1];
          }
        }
      }
    }

    // Clean remaining export keywords
    processed = processed.replace(/export\s+(?:const|let|var|function)\s+/g, (match) => {
      return match.replace('export ', '');
    });

    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline' https:; script-src 'unsafe-inline' 'unsafe-eval' https:; font-src https: data:; img-src data: https:;">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style>
    body {
      margin: 0;
      padding: 24px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: #0c0d10;
      color: #f3f4f6;
      min-height: 100vh;
    }
  </style>
</head>
<body>
  <div id="root"></div>
  <div id="error-container" style="display:none; padding:16px; background:#1c1314; border:1px solid #7f1d1d; color:#fca5a5; border-radius:6px; font-family:monospace; font-size:13px; margin:16px;"></div>

  <script>
    window.onerror = function(message, source, lineno, colno, error) {
      var box = document.getElementById('error-container');
      if (box) {
        box.style.display = 'block';
        box.innerText = 'Render Error: ' + message;
      }
    };
  </script>

  <script type="text/babel">
    const { useState, useEffect, useRef, useMemo, useCallback, useReducer } = React;

    ${processed}

    try {
      const rootEl = document.getElementById('root');
      if (rootEl && typeof ReactDOM !== 'undefined') {
        const root = ReactDOM.createRoot(rootEl);
        if (typeof ${componentName} !== 'undefined') {
          root.render(<${componentName} />);
        }
      }
    } catch (err) {
      var box = document.getElementById('error-container');
      if (box) {
        box.style.display = 'block';
        box.innerText = 'Render Exception: ' + err.message;
      }
    }
  </script>
</body>
</html>`;
  };

  const renderedMarkdownHtml = DOMPurify.sanitize(marked.parse(artifact.content) as string);

  return (
    <aside className="artifact-pane" aria-label="Artifact Viewer">
      <header className="artifact-pane-header">
        <div className="artifact-header-left">
          <span className="artifact-title" title={artifact.title}>
            {artifact.title}
          </span>
          <span className="artifact-word-badge">
            {artifact.type.toUpperCase()} · {artifact.word_count.toLocaleString()} words
          </span>
        </div>

        <div className="artifact-controls">
          <div className="view-toggle-group">
            <button
              className={`view-toggle-btn ${viewMode === 'rendered' ? 'active' : ''}`}
              onClick={() => setViewMode('rendered')}
              title="Rendered interactive view"
            >
              <Eye size={13} style={{ marginRight: 4 }} />
              Preview
            </button>
            <button
              className={`view-toggle-btn ${viewMode === 'raw' ? 'active' : ''}`}
              onClick={() => setViewMode('raw')}
              title="Raw code view"
            >
              <Code2 size={13} style={{ marginRight: 4 }} />
              Raw
            </button>
          </div>

          <button
            className="icon-btn"
            onClick={handleCopy}
            title={copied ? 'Copied to clipboard!' : 'Copy raw content'}
          >
            {copied ? <Check size={16} color="var(--success)" /> : <Copy size={16} />}
          </button>

          <button
            className="icon-btn"
            onClick={onClose}
            title="Close viewer"
          >
            <X size={18} />
          </button>
        </div>
      </header>

      <div className="artifact-content-container">
        {viewMode === 'raw' ? (
          <pre className="artifact-raw-markdown">{artifact.content}</pre>
        ) : artifact.type === 'react' ? (
          <iframe
            title={artifact.title}
            srcDoc={buildSandboxedReact(artifact.content)}
            sandbox="allow-scripts"
            className="artifact-sandboxed-iframe"
          />
        ) : artifact.type === 'html' ? (
          <iframe
            title={artifact.title}
            srcDoc={buildSandboxedHtml(artifact.content)}
            sandbox="allow-scripts"
            className="artifact-sandboxed-iframe"
          />
        ) : (
          <div
            className="artifact-rendered-markdown markdown-body"
            dangerouslySetInnerHTML={{ __html: renderedMarkdownHtml }}
          />
        )}
      </div>
    </aside>
  );
};
