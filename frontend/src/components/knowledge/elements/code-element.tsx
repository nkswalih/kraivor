'use client';

import dynamic from 'next/dynamic';
import { memo, type ComponentType } from 'react';
import type { CodeElementData } from '@/types/knowledge';

const MonacoEditor = dynamic(() => import('@monaco-editor/react').then(mod => mod.Editor), {
  ssr: false,
  loading: () => <div className="w-full h-full bg-krait-surface3 animate-pulse" />,
}) as ComponentType<Record<string, unknown>>;

interface Props {
  data: CodeElementData;
}

export const CodeElement = memo(function CodeElement({ data }: Props) {
  return (
    <div
      className="w-full h-full overflow-hidden"
      style={{ backgroundColor: data.backgroundColor ?? 'var(--krait-surface-1)' }}
    >
      <div className="flex items-center justify-between px-3 py-1.5 bg-krait-surface3 border-b border-border">
        <span className="text-[11px] text-text-tertiary font-mono uppercase tracking-wider">
          {data.language ?? 'text'}
        </span>
      </div>
      <div className="h-[calc(100%-32px)]">
        <MonacoEditor
          defaultLanguage={data.language ?? 'plaintext'}
          defaultValue={data.code ?? ''}
          theme={data.theme === 'light' ? 'vs' : 'vs-dark'}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: data.showLineNumbers ? 'on' : 'off',
            scrollBeyondLastLine: false,
            padding: { top: 8 },
          }}
        />
      </div>
    </div>
  );
}, (prev, next) =>
  prev.data.code === next.data.code &&
  prev.data.language === next.data.language &&
  prev.data.backgroundColor === next.data.backgroundColor &&
  prev.data.theme === next.data.theme &&
  prev.data.showLineNumbers === next.data.showLineNumbers
);
