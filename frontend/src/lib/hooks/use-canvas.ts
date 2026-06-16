'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import { useSaveCanvas } from './use-knowledge';

const AUTOSAVE_DELAY = 3000;

export function useCanvasAutosave(
  spaceId: string | undefined,
  knowledgeId: string,
  workspaceId: string,
  spaceName?: string,
  spaceDescription?: string | null,
) {
  const saveCanvas = useSaveCanvas(knowledgeId, workspaceId);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const savingRef = useRef(false);
  const isDirty = useKnowledgeStore(s =>
    spaceId ? !!s.dirtySpaceIds[spaceId] : false
  );
  const getCanvasState = useKnowledgeStore(s => s.getCanvasState);
  const markClean = useKnowledgeStore(s => s.markClean);
  const setSaving = useKnowledgeStore(s => s.setSaving);
  const setLastSavedAt = useKnowledgeStore(s => s.setLastSavedAt);

  const flush = useCallback(() => {
    if (!spaceId || savingRef.current) return;
    const state = getCanvasState(spaceId);
    if (!state) return;
    savingRef.current = true;
    setSaving(true);
    saveCanvas.mutate(
      {
        name: spaceName ?? 'Untitled',
        description: spaceDescription ?? '',
        canvas_data: {
          elements: state.elements,
          viewport: state.viewport,
          gridEnabled: state.gridEnabled,
          snapEnabled: state.snapEnabled,
          gridSize: state.gridSize,
        },
      },
      {
        onSuccess: () => {
          setLastSavedAt(new Date().toISOString());
        },
        onSettled: () => {
          savingRef.current = false;
          markClean(spaceId);
          setSaving(false);
        },
      }
    );
  }, [spaceId, getCanvasState, markClean, setSaving, saveCanvas, spaceName, spaceDescription, setLastSavedAt]);

  const flushRef = useRef(flush);
  flushRef.current = flush;

  useEffect(() => {
    if (!isDirty || !spaceId || savingRef.current) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => flushRef.current(), AUTOSAVE_DELAY);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isDirty, spaceId]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (!savingRef.current) flushRef.current();
    };
  }, []);
}

export function useCanvasKeyboard(spaceId: string | undefined) {
  const store = useKnowledgeStore;

  useEffect(() => {
    if (!spaceId) return;

    const handleKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.contentEditable === 'true') return;

      const state = store.getState();
      const canvas = state.spaces[spaceId];
      if (!canvas) return;
      const selected = canvas.selectedElementIds;

      const isCtrl = e.metaKey || e.ctrlKey;

      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selected.length === 0) return;
        e.preventDefault();
        state.pushUndoState(spaceId);
        state.deleteSelectedElements(spaceId);
        return;
      }

      if (e.key === 'z' && isCtrl && !e.shiftKey) {
        e.preventDefault();
        state.undo(spaceId);
        return;
      }

      if (e.key === 'z' && isCtrl && e.shiftKey) {
        e.preventDefault();
        state.redo(spaceId);
        return;
      }

      if (e.key === 'd' && isCtrl) {
        e.preventDefault();
        selected.forEach(id => state.duplicateElement(spaceId, id));
        return;
      }

      if (e.key === 'Escape') {
        state.clearSelection(spaceId);
      }
    };

    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [spaceId, store]);
}

export function useCanvasHistory(spaceId: string | undefined) {
  const updateElement = useKnowledgeStore(s => s.updateElement);
  const removeElement = useKnowledgeStore(s => s.removeElement);
  const addElement = useKnowledgeStore(s => s.addElement);
  const spaces = useKnowledgeStore(s => s.spaces);

  const saveSnapshot = useCallback(() => {
    if (!spaceId) return null;
    const canvas = spaces[spaceId];
    if (!canvas) return null;
    return JSON.stringify({ elements: canvas.elements, viewport: canvas.viewport });
  }, [spaceId, spaces]);

  return { saveSnapshot };
}
