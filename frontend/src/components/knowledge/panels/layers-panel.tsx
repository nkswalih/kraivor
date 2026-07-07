'use client';

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import { Eye, EyeOff, Lock, Unlock, GripVertical, ArrowUp, ArrowDown } from 'lucide-react';

interface Props {
  spaceId: string;
}

export function LayersPanel({ spaceId }: Props) {
  const elements = useKnowledgeStore(s => s.spaces[spaceId]?.elements ?? []);
  const selectedIds = useKnowledgeStore(s => s.spaces[spaceId]?.selectedElementIds ?? []);
  const setSelectedElements = useKnowledgeStore(s => s.setSelectedElements);
  const toggleElementVisibility = useKnowledgeStore(s => s.toggleElementVisibility);
  const lockElement = useKnowledgeStore(s => s.lockElement);
  const bringForward = useKnowledgeStore(s => s.bringForward);
  const sendBackward = useKnowledgeStore(s => s.sendBackward);

  const sorted = useMemo(
    () => [...elements].sort((a, b) => b.zIndex - a.zIndex),
    [elements]
  );

  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent, idx: number) => {
      e.preventDefault();
      const elementId = e.dataTransfer.getData('text/plain');
      if (!elementId) return;

      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      const insertBefore = e.clientY < rect.top + rect.height / 2;
      const dropDisplayIdx = insertBefore ? idx : idx + 1;

      const store = useKnowledgeStore.getState();
      const s = store.spaces[spaceId];
      if (!s) return;

      const displayList = [...s.elements].sort((a, b) => b.zIndex - a.zIndex);
      const draggedDisplayIdx = displayList.findIndex(el => el.id === elementId);
      if (draggedDisplayIdx === -1) return;

      store.pushUndoState(spaceId);

      const [moved] = displayList.splice(draggedDisplayIdx, 1);
      const adjustedDropIdx =
        draggedDisplayIdx < dropDisplayIdx ? dropDisplayIdx - 1 : dropDisplayIdx;
      displayList.splice(adjustedDropIdx, 0, moved);

      displayList.forEach((el, di) => {
        store.updateElement(spaceId, el.id, { zIndex: displayList.length - di });
      });

      setDragOverIdx(null);
      setDraggedId(null);
    },
    [spaceId]
  );

  const startEditing = (id: string, currentName: string) => {
    setEditingId(id);
    setEditValue(currentName);
  };

  const saveName = () => {
    if (!editingId) return;
    const trimmed = editValue.trim();
    const store = useKnowledgeStore.getState();
    if (trimmed) {
      store.updateElement(spaceId, editingId, { name: trimmed });
    } else {
      store.updateElement(spaceId, editingId, { name: undefined });
    }
    setEditingId(null);
    setEditValue('');
  };

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  return (
    <div className="p-3 space-y-3 overflow-y-auto">
      <h3 className="text-[11px] font-semibold tracking-wider text-text-tertiary uppercase">
        Layers
      </h3>
      {sorted.length === 0 ? (
        <p className="text-[13px] text-text-tertiary text-center py-4">No elements on canvas</p>
      ) : (
        <div className="space-y-0.5">
          {sorted.map((el, idx) => {
            const isSelected = selectedIds.includes(el.id);
            const isEditing = editingId === el.id;

            return (
              <div key={el.id}>
                {dragOverIdx === idx && (
                  <div className="h-0.5 bg-venom-yellow rounded-full my-0.5" />
                )}
                <div
                  draggable
                  onDragStart={e => {
                    e.dataTransfer.effectAllowed = 'move';
                    e.dataTransfer.setData('text/plain', el.id);
                    setDraggedId(el.id);
                  }}
                  onDragOver={e => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = 'move';
                    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                    const insertBefore = e.clientY < rect.top + rect.height / 2;
                    setDragOverIdx(insertBefore ? idx : idx + 1);
                  }}
                  onDragLeave={e => {
                    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
                      setDragOverIdx(null);
                    }
                  }}
                  onDrop={e => handleDrop(e, idx)}
                  onDragEnd={() => {
                    setDragOverIdx(null);
                    setDraggedId(null);
                  }}
                  onClick={() => {
                    if (!isEditing) setSelectedElements(spaceId, [el.id]);
                  }}
                  className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg cursor-grab active:cursor-grabbing group
                    ${isSelected ? 'bg-venom-yellow/10 ring-1 ring-venom-yellow/30' : 'hover:bg-krait-surface3'}
                    ${draggedId === el.id ? 'opacity-40' : ''}
                    transition-colors`}
                >
                  <GripVertical className="w-3 h-3 text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity shrink-0 cursor-grab" />
                  <span className="text-[12px] font-mono text-text-tertiary w-5 shrink-0 text-right">
                    {elements.length - idx}
                  </span>
                  {isEditing ? (
                    <input
                      ref={inputRef}
                      type="text"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      onBlur={saveName}
                      onKeyDown={e => {
                        if (e.key === 'Enter') saveName();
                        if (e.key === 'Escape') setEditingId(null);
                        e.stopPropagation();
                      }}
                      onClick={e => e.stopPropagation()}
                      className="flex-1 text-[13px] bg-krait-surface2 border border-venom-yellow/50 rounded px-1 py-0.5 text-foreground outline-none min-w-0 ml-1"
                    />
                  ) : (
                    <span
                      className="text-[13px] text-foreground flex-1 truncate ml-1"
                      onDoubleClick={e => {
                        e.stopPropagation();
                        startEditing(el.id, el.name ?? el.type.replace('_', ' '));
                      }}
                    >
                      {el.name ?? el.type.replace('_', ' ')}
                    </span>
                  )}
                  <div className="flex items-center gap-0.5 shrink-0">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        bringForward(spaceId, el.id);
                      }}
                      className="p-0.5 text-text-tertiary hover:text-foreground"
                      title="Bring forward"
                    >
                      <ArrowUp className="w-3 h-3" />
                    </button>
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        sendBackward(spaceId, el.id);
                      }}
                      className="p-0.5 text-text-tertiary hover:text-foreground"
                      title="Send backward"
                    >
                      <ArrowDown className="w-3 h-3" />
                    </button>
                  </div>
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      toggleElementVisibility(spaceId, el.id);
                    }}
                    className="p-0.5 text-text-tertiary hover:text-foreground"
                  >
                    {el.visible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                  </button>
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      lockElement(spaceId, el.id, !el.locked);
                    }}
                    className={`p-0.5 ${el.locked ? 'text-venom-yellow' : 'text-text-tertiary hover:text-foreground'}`}
                  >
                    {el.locked ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
                  </button>
                </div>
              </div>
            );
          })}
          {dragOverIdx === sorted.length && (
            <div className="h-0.5 bg-venom-yellow rounded-full my-0.5" />
          )}
        </div>
      )}
    </div>
  );
}
