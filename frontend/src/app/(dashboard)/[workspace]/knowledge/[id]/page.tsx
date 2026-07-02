'use client';

import { useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import { useKnowledgeDetail } from '@/lib/hooks/use-knowledge';
import { useCanvasAutosave } from '@/lib/hooks/use-canvas';
import { useDetailBreadcrumb } from '@/lib/hooks/use-detail-breadcrumb';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import { KnowledgeCanvas } from '@/components/knowledge/canvas/knowledge-canvas';
import { CanvasSidebar } from '@/components/knowledge/canvas/canvas-sidebar';
import { BookOpen, Loader2, Save, ArrowLeft } from 'lucide-react';
import type { CanvasState } from '@/types/knowledge';

const CANVAS_ID_PREFIX = 'knowledge-';

export default function KnowledgeDetailPage() {
  const params = useParams<{ id: string; workspace: string }>();
  const id = params?.id ?? '';
  const workspaceSlug = params?.workspace ?? '';
  const spaceId = `${CANVAS_ID_PREFIX}${id}`;

  const initCanvas = useKnowledgeStore(s => s.initCanvas);
  const setActiveSpace = useKnowledgeStore(s => s.setActiveSpace);
  const isSaving = useKnowledgeStore(s => s.isSaving);
  const lastSavedAt = useKnowledgeStore(s => s.lastSavedAt);
  const dirtySpaceIds = useKnowledgeStore(s => s.dirtySpaceIds);

  const { data: space, isLoading } = useKnowledgeDetail(id || undefined);
  useDetailBreadcrumb(space?.name);

  const workspaceId = space?.workspace_id ?? '';

  useCanvasAutosave(spaceId, id, workspaceId, space?.name, space?.description ?? null);

  const canvasInitialized = useRef(false);
  useEffect(() => {
    if (!space || !id) return;
    if (canvasInitialized.current) return;
    canvasInitialized.current = true;
    setActiveSpace(spaceId);
    const existingCanvas = space.canvas_data as Partial<CanvasState> | undefined;
    initCanvas(spaceId, {
      elements: (existingCanvas?.elements as CanvasState['elements']) ?? [],
      viewport: (existingCanvas?.viewport as CanvasState['viewport']) ?? { x: 0, y: 0, zoom: 1 },
      gridEnabled: ((existingCanvas as Record<string, unknown>)?.gridEnabled as boolean) ?? true,
      snapEnabled: ((existingCanvas as Record<string, unknown>)?.snapEnabled as boolean) ?? true,
      gridSize: ((existingCanvas as Record<string, unknown>)?.gridSize as number) ?? 20,
    });
  }, [space, id, spaceId, setActiveSpace, initCanvas]);

  useEffect(() => {
    return () => {
      canvasInitialized.current = false;
      useKnowledgeStore.getState().destroyCanvas(spaceId);
    };
  }, [spaceId]);

  const isDirty = dirtySpaceIds[spaceId] ?? false;

  const saveIndicator = () => {
    if (isSaving) {
      return (
        <span className="flex items-center gap-1.5 text-[11px] text-venom-yellow">
          <Loader2 className="w-3 h-3 animate-spin" /> Saving...
        </span>
      );
    }
    if (isDirty) {
      return (
        <span className="flex items-center gap-1.5 text-[11px] text-text-tertiary">
          Unsaved changes
        </span>
      );
    }
    if (lastSavedAt) {
      return (
        <span className="flex items-center gap-1.5 text-[11px] text-green-400">
          <Save className="w-3 h-3" /> Saved
        </span>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-krait-surface3 animate-pulse" />
            <div className="w-40 h-5 rounded bg-krait-surface3 animate-pulse" />
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center bg-krait-void">
          <Loader2 className="w-6 h-6 text-venom-yellow animate-spin" />
        </div>
      </div>
    );
  }

  if (!space) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <BookOpen className="w-10 h-10 text-muted-foreground mb-3" />
        <h3 className="text-base font-medium text-foreground mb-1">Space not found</h3>
        <a
          href={`/${workspaceSlug}/knowledge`}
          className="text-[13px] text-venom-yellow hover:text-venom-gold mt-2"
        >
          Back to knowledge spaces
        </a>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-krait-surface1 shrink-0">
        <div className="flex items-center gap-3">
          <a
            href={`/${workspaceSlug}/knowledge`}
            className="p-1.5 text-text-tertiary hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </a>
          <div className="w-7 h-7 rounded-lg bg-venom-yellow/10 flex items-center justify-center">
            <BookOpen className="w-3.5 h-3.5 text-venom-yellow" />
          </div>
          <div>
            <h1 className="text-[14px] font-medium text-foreground leading-tight">{space.name}</h1>
            {space.description && (
              <p className="text-[11px] text-text-tertiary leading-tight">{space.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">{saveIndicator()}</div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <KnowledgeCanvas spaceId={spaceId} />
        <CanvasSidebar spaceId={spaceId} />
      </div>
    </div>
  );
}
