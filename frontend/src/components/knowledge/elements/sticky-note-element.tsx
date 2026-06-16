'use client';

import { useRef, useEffect, useCallback } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import type { StickyNoteElementData, CanvasElement } from '@/types/knowledge';

interface Props {
  data: StickyNoteElementData;
  elementId: string;
  spaceId: string;
  isEditing: boolean;
  onEditEnd: () => void;
}

export function StickyNoteElement({ data, elementId, spaceId, isEditing, onEditEnd }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const updateElement = useKnowledgeStore(s => s.updateElement);

  useEffect(() => {
    if (isEditing && ref.current) {
      ref.current.focus();
      const sel = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(ref.current);
      sel?.removeAllRanges();
      sel?.addRange(range);
    }
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
      className="w-full h-full p-4 flex items-start outline-none overflow-auto"
      contentEditable={isEditing}
      suppressContentEditableWarning
      style={{
        backgroundColor: data.color ?? '#fef08a',
        fontSize: data.fontSize ?? 14,
        color: '#1c1917',
        whiteSpace: 'pre-wrap',
        overflowWrap: 'break-word',
        cursor: isEditing ? 'text' : 'default',
        userSelect: isEditing ? 'text' : 'none',
      }}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
    >
      {data.text}
    </div>
  );
}
