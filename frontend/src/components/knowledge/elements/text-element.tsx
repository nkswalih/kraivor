'use client';

import { useRef, useEffect, useCallback } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import type { TextElementData, CanvasElement } from '@/types/knowledge';

interface Props {
  data: TextElementData;
  elementId: string;
  spaceId: string;
  isEditing: boolean;
  onEditEnd: () => void;
}

export function TextElement({ data, elementId, spaceId, isEditing, onEditEnd }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const updateElement = useKnowledgeStore(s => s.updateElement);

  useEffect(() => {
    if (!isEditing || !ref.current) return;
    const el = ref.current;
    el.contentEditable = 'true';
    requestAnimationFrame(() => {
      el.focus();
      const sel = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(el);
      range.collapse(false);
      sel?.removeAllRanges();
      sel?.addRange(range);
    });
  }, [isEditing]);

  const save = useCallback(() => {
    const text = ref.current?.textContent ?? '';
    updateElement(spaceId, elementId, {
      data: { ...data, text } as unknown as CanvasElement['data'],
    });
  }, [spaceId, elementId, data, updateElement]);

  const handleBlur = useCallback(() => {
    save();
    onEditEnd();
  }, [save, onEditEnd]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      save();
      onEditEnd();
    }
  }, [save, onEditEnd]);

  return (
    <div
      ref={ref}
      className="w-full h-full outline-none overflow-auto"
      style={{
        fontSize: data.fontSize ?? 14,
        fontWeight: data.fontWeight ?? 'normal',
        fontFamily: data.fontFamily ?? 'inherit',
        color: data.color ?? 'var(--foreground)',
        backgroundColor: data.backgroundColor ?? undefined,
        textAlign: data.textAlign ?? 'left',
        padding: data.padding ?? 12,
        whiteSpace: 'pre-wrap',
        overflowWrap: 'break-word',
        cursor: isEditing ? 'text' : 'default',
        userSelect: 'text',
        WebkitUserSelect: 'text',
      }}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
    >
      {data.text}
    </div>
  );
}
