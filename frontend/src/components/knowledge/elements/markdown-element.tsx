'use client';

import ReactMarkdown from 'react-markdown';
import type { MarkdownElementData } from '@/types/knowledge';

interface Props {
  data: MarkdownElementData;
}

export function MarkdownElement({ data }: Props) {
  return (
    <div
      className="w-full h-full p-4 overflow-y-auto bg-krait-surface1 prose prose-invert prose-sm max-w-none"
      style={{
        backgroundColor: data.backgroundColor ?? undefined,
      }}
    >
      <ReactMarkdown>{data.source}</ReactMarkdown>
    </div>
  );
}
