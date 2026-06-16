'use client';

import { useState } from 'react';
import { Type, FileText, Terminal, Image, StickyNote, X } from 'lucide-react';
import type { CanvasElementType } from '@/types/knowledge';

interface Props {
  open: boolean;
  onClose: () => void;
  onSelect: (type: CanvasElementType) => void;
}

const elementTypes: Array<{ type: CanvasElementType; label: string; description: string; icon: typeof Type }> = [
  { type: 'text', label: 'Text', description: 'Simple text block', icon: Type },
  { type: 'markdown', label: 'Markdown', description: 'Rich formatted text', icon: FileText },
  { type: 'code', label: 'Code', description: 'Syntax-highlighted code', icon: Terminal },
  { type: 'image', label: 'Image', description: 'Image from assets', icon: Image },
  { type: 'sticky_note', label: 'Sticky Note', description: 'Colored note', icon: StickyNote },
];

export function CreateElementDialog({ open, onClose, onSelect }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-[400px] rounded-xl border border-border bg-krait-surface1 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-[15px] font-medium text-foreground">Add Element</h2>
          <button onClick={onClose} className="p-1 text-text-tertiary hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4 grid grid-cols-2 gap-2">
          {elementTypes.map(et => (
            <button
              key={et.type}
              onClick={() => { onSelect(et.type); onClose(); }}
              className="flex flex-col items-center gap-2 p-4 rounded-lg border border-border bg-krait-surface2 hover:bg-krait-surface3 hover:border-venom-yellow/30 transition-all text-center group"
            >
              <et.icon className="w-6 h-6 text-venom-yellow group-hover:scale-110 transition-transform" />
              <span className="text-[13px] font-medium text-foreground">{et.label}</span>
              <span className="text-[11px] text-text-tertiary">{et.description}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
