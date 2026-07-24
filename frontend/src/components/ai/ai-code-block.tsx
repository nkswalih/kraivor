'use client';

import { useState, useCallback } from 'react';
import { Check, Copy, ChevronDown, ChevronRight, WrapText } from 'lucide-react';

interface AiCodeBlockProps {
  code: string;
  language?: string;
}

export function AiCodeBlock({ code, language }: AiCodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [wrapped, setWrapped] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const lineCount = code.split('\n').length;
  const isLarge = lineCount > 20;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  }, [code]);

  return (
    <div className="group/code my-4 rounded-xl border border-krait-border bg-[#0D0D10] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-krait-border bg-[#111114]">
        <div className="flex items-center gap-2">
          {language && (
            <span className="text-[11px] font-mono font-medium text-text-tertiary uppercase tracking-wider">
              {language}
            </span>
          )}
          {isLarge && (
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="flex items-center gap-1 text-[11px] text-text-tertiary hover:text-text-secondary transition-colors"
            >
              {collapsed ? (
                <ChevronRight className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
              {lineCount} lines
            </button>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setWrapped(!wrapped)}
            className={`p-1.5 rounded-md transition-colors ${
              wrapped
                ? 'text-venom-yellow bg-venom-yellow/10'
                : 'text-text-tertiary hover:text-text-secondary hover:bg-krait-surface3'
            }`}
            title="Toggle word wrap"
          >
            <WrapText className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-md text-text-tertiary hover:text-text-secondary hover:bg-krait-surface3 transition-colors"
            title="Copy code"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-venom-yellow" strokeWidth={1.5} />
            ) : (
              <Copy className="w-3.5 h-3.5" strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>

      {/* Code body */}
      {(!isLarge || !collapsed) && (
        <div className="relative">
          <pre
            className={`${
              wrapped ? 'whitespace-pre-wrap' : 'whitespace-pre overflow-x-auto'
            } p-4 text-[13px] leading-[1.65] font-mono text-[#d1d5db]`}
          >
            <code>{code}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
