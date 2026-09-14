import React from 'react';
import { ExternalLink } from 'lucide-react';
import type { Citation } from '../types';

interface CitationBadgeProps {
  citation: Citation;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citation }) => {
  return (
    <a
      href={citation.youtube_url}
      target="_blank"
      rel="noopener noreferrer"
      className="citation-chip"
      title={`${citation.guest} on "${citation.episode_title}" (${citation.start_timestamp}) - Click to play on YouTube`}
    >
      <span>{citation.guest}</span>
      <span className="chip-time">{citation.start_timestamp}</span>
      <ExternalLink size={11} style={{ opacity: 0.7 }} />
    </a>
  );
};
