import { create } from 'zustand';
import { produce } from 'immer';
import { nanoid } from 'nanoid';
import type {
  CanvasElement,
  CanvasElementType,
  CanvasState,
  Position,
  ShapeType,
  Size,
} from '@/types/knowledge';

type CanvasSnapshot = Pick<CanvasState, 'elements'>;

interface KnowledgeStore {
  spaces: Record<string, CanvasState>;
  activeSpaceId: string | null;
  dirtySpaceIds: Record<string, boolean>;
  isSaving: boolean;
  selectedTool: 'select' | 'hand' | 'text' | 'sticky_note' | 'rectangle' | 'arrow' | 'flowchart';
  subTool: ShapeType;
  activePanel: 'properties' | 'layers' | 'assets' | 'ai' | null;
  sidebarWidth: number;
  showSidebar: boolean;
  showMinimap: boolean;
  editingElementId: string | null;
  lastSavedAt: string | null;
  arrowStart: { elementId: string; point: Position } | null;
  undoStack: CanvasSnapshot[];
  redoStack: CanvasSnapshot[];
  setLastSavedAt: (ts: string | null) => void;

  setActiveSpace: (spaceId: string) => void;
  setEditingElementId: (id: string | null) => void;
  initCanvas: (spaceId: string, existingState?: Partial<CanvasState>) => void;
  destroyCanvas: (spaceId: string) => void;

  addElement: (spaceId: string, type: CanvasElementType, position: Position, size: Size, data?: Record<string, unknown>) => string;
  updateElement: (spaceId: string, elementId: string, changes: Partial<CanvasElement>) => void;
  removeElement: (spaceId: string, elementId: string) => void;
  moveElement: (spaceId: string, elementId: string, position: Position) => void;
  resizeElement: (spaceId: string, elementId: string, size: Size) => void;
  duplicateElement: (spaceId: string, elementId: string) => void;
  lockElement: (spaceId: string, elementId: string, locked: boolean) => void;
  toggleElementVisibility: (spaceId: string, elementId: string) => void;
  reorderElement: (spaceId: string, elementId: string, zIndex: number) => void;
  deleteSelectedElements: (spaceId: string) => void;
  bringForward: (spaceId: string, elementId: string) => void;
  sendBackward: (spaceId: string, elementId: string) => void;

  setSelectedElements: (spaceId: string, elementIds: string[]) => void;
  clearSelection: (spaceId: string) => void;

  setViewport: (spaceId: string, viewport: CanvasState['viewport']) => void;

  setSelectedTool: (tool: KnowledgeStore['selectedTool']) => void;
  setSubTool: (tool: ShapeType) => void;
  setActivePanel: (panel: KnowledgeStore['activePanel']) => void;
  setSidebarWidth: (width: number) => void;
  toggleSidebar: () => void;
  toggleMinimap: () => void;
  toggleGrid: (spaceId: string) => void;
  toggleSnap: (spaceId: string) => void;
  zoomTo: (spaceId: string, zoom: number) => void;
  zoomIn: (spaceId: string) => void;
  zoomOut: (spaceId: string) => void;

  pushUndoState: (spaceId: string) => void;
  undo: (spaceId: string) => void;
  redo: (spaceId: string) => void;

  setArrowStart: (elementId: string, point: Position) => void;
  clearArrowStart: () => void;

  markDirty: (spaceId: string) => void;
  markClean: (spaceId: string) => void;
  setSaving: (saving: boolean) => void;
  getCanvasState: (spaceId: string) => CanvasState | null;
}

function createDefaultState(): CanvasState {
  return {
    elements: [],
    viewport: { x: 0, y: 0, zoom: 1 },
    selectedElementIds: [],
    clipboard: null,
    gridEnabled: true,
    snapEnabled: true,
    gridSize: 20,
  };
}

function findHighestZIndex(elements: CanvasElement[]): number {
  if (elements.length === 0) return 0;
  return Math.max(...elements.map(e => e.zIndex));
}

function takeSnapshot(canvas: CanvasState): CanvasSnapshot {
  return { elements: JSON.parse(JSON.stringify(canvas.elements)) };
}

export const useKnowledgeStore = create<KnowledgeStore>((set, get) => ({
  spaces: {},
  activeSpaceId: null,
  dirtySpaceIds: {},
  isSaving: false,
  selectedTool: 'select',
  subTool: 'rectangle',
  activePanel: 'properties',
  sidebarWidth: 300,
  showSidebar: true,
  showMinimap: true,
  editingElementId: null,
  lastSavedAt: null,
  arrowStart: null,
  undoStack: [],
  redoStack: [],

  setActiveSpace: (spaceId) => {
    set({ activeSpaceId: spaceId });
  },

  setEditingElementId: (id) => {
    set({ editingElementId: id });
  },

  setLastSavedAt: (ts) => {
    set({ lastSavedAt: ts });
  },

  initCanvas: (spaceId, existingState) => {
    set(produce((state: KnowledgeStore) => {
      if (!state.spaces[spaceId]) {
        state.spaces[spaceId] = {
          ...createDefaultState(),
          ...existingState,
        };
      }
    }));
  },

  destroyCanvas: (spaceId) => {
    set(produce((state: KnowledgeStore) => {
      delete state.spaces[spaceId];
      delete state.dirtySpaceIds[spaceId];
      if (state.activeSpaceId === spaceId) {
        state.activeSpaceId = null;
      }
    }));
  },

  addElement: (spaceId, type, position, size, data) => {
    const id = nanoid();
    const now = new Date().toISOString();
    set(produce((state: KnowledgeStore) => {
      const canvas = state.spaces[spaceId];
      if (!canvas) return;
      const element: CanvasElement = {
        id,
        type,
        position,
        size,
        rotation: 0,
        zIndex: findHighestZIndex(canvas.elements) + 1,
        locked: false,
        visible: true,
        opacity: 1,
        data: data ?? {},
        createdAt: now,
        updatedAt: now,
        createdBy: '',
      };
      canvas.elements.push(element);
      canvas.selectedElementIds = [id];
    }));
    get().markDirty(spaceId);
    return id;
  },

  updateElement: (spaceId, elementId, changes) => {
    set(produce((state: KnowledgeStore) => {
      const canvas = state.spaces[spaceId];
      if (!canvas) return;
      const idx = canvas.elements.findIndex(e => e.id === elementId);
      if (idx === -1) return;
      Object.assign(canvas.elements[idx], changes, {
        updatedAt: new Date().toISOString(),
      });
    }));
    get().markDirty(spaceId);
  },

  removeElement: (spaceId, elementId) => {
    set(produce((state: KnowledgeStore) => {
      const canvas = state.spaces[spaceId];
      if (!canvas) return;
      canvas.elements = canvas.elements.filter(e => e.id !== elementId);
      canvas.selectedElementIds = canvas.selectedElementIds.filter(id => id !== elementId);
    }));
    get().markDirty(spaceId);
  },

  moveElement: (spaceId, elementId, position) => {
    get().updateElement(spaceId, elementId, { position, updatedAt: new Date().toISOString() });
  },

  resizeElement: (spaceId, elementId, size) => {
    get().updateElement(spaceId, elementId, { size, updatedAt: new Date().toISOString() });
  },

  duplicateElement: (spaceId, elementId) => {
    const canvas = get().spaces[spaceId];
    if (!canvas) return;
    const source = canvas.elements.find(e => e.id === elementId);
    if (!source) return;
    const id = nanoid();
    const now = new Date().toISOString();
    set(produce((state: KnowledgeStore) => {
      const c = state.spaces[spaceId];
      if (!c) return;
      const dup: CanvasElement = {
        ...source,
        id,
        position: { x: source.position.x + 30, y: source.position.y + 30 },
        zIndex: findHighestZIndex(c.elements) + 1,
        createdAt: now,
        updatedAt: now,
      };
      c.elements.push(dup);
      c.selectedElementIds = [id];
    }));
    get().markDirty(spaceId);
  },

  lockElement: (spaceId, elementId, locked) => {
    get().updateElement(spaceId, elementId, { locked });
  },

  toggleElementVisibility: (spaceId, elementId) => {
    const canvas = get().spaces[spaceId];
    if (!canvas) return;
    const el = canvas.elements.find(e => e.id === elementId);
    if (!el) return;
    get().updateElement(spaceId, elementId, { visible: !el.visible });
  },

  reorderElement: (spaceId, elementId, zIndex) => {
    get().updateElement(spaceId, elementId, { zIndex });
  },

  deleteSelectedElements: (spaceId) => {
    const canvas = get().spaces[spaceId];
    if (!canvas) return;
    const ids = canvas.selectedElementIds;
    if (ids.length === 0) return;
    const idSet = new Set(ids);
    set(produce((state: KnowledgeStore) => {
      const c = state.spaces[spaceId];
      if (!c) return;
      c.elements = c.elements.filter(e => !idSet.has(e.id));
      c.selectedElementIds = [];
    }));
    get().markDirty(spaceId);
  },

  bringForward: (spaceId, elementId) => {
    const canvas = get().spaces[spaceId];
    if (!canvas) return;
    const el = canvas.elements.find(e => e.id === elementId);
    if (!el) return;
    const maxZ = findHighestZIndex(canvas.elements);
    if (el.zIndex >= maxZ) return;
    get().updateElement(spaceId, elementId, { zIndex: el.zIndex + 1 });
  },

  sendBackward: (spaceId, elementId) => {
    const canvas = get().spaces[spaceId];
    if (!canvas) return;
    const el = canvas.elements.find(e => e.id === elementId);
    if (!el) return;
    if (el.zIndex <= 1) return;
    get().updateElement(spaceId, elementId, { zIndex: el.zIndex - 1 });
  },

  setSelectedElements: (spaceId, elementIds) => {
    set(produce((state: KnowledgeStore) => {
      const canvas = state.spaces[spaceId];
      if (!canvas) return;
      canvas.selectedElementIds = elementIds;
    }));
  },

  clearSelection: (spaceId) => {
    set(produce((state: KnowledgeStore) => {
      const canvas = state.spaces[spaceId];
      if (!canvas) return;
      canvas.selectedElementIds = [];
    }));
  },

  setViewport: (spaceId, viewport) => {
    set(produce((state: KnowledgeStore) => {
      const canvas = state.spaces[spaceId];
      if (!canvas) return;
      canvas.viewport = viewport;
    }));
  },

  setSelectedTool: (tool) => set({ selectedTool: tool, arrowStart: null }),
  setSubTool: (tool) => set({ subTool: tool }),
  setActivePanel: (panel) => set({ activePanel: panel }),
  setSidebarWidth: (width) => set({ sidebarWidth: width }),
  toggleSidebar: () => set(s => ({ showSidebar: !s.showSidebar })),
  toggleMinimap: () => set(s => ({ showMinimap: !s.showMinimap })),

  toggleGrid: (spaceId) => {
    set(produce((state: KnowledgeStore) => {
      const c = state.spaces[spaceId];
      if (!c) return;
      c.gridEnabled = !c.gridEnabled;
    }));
  },

  toggleSnap: (spaceId) => {
    set(produce((state: KnowledgeStore) => {
      const c = state.spaces[spaceId];
      if (!c) return;
      c.snapEnabled = !c.snapEnabled;
    }));
  },

  zoomTo: (spaceId, zoom) => {
    set(produce((state: KnowledgeStore) => {
      const c = state.spaces[spaceId];
      if (!c) return;
      c.viewport.zoom = Math.max(0.1, Math.min(3, zoom));
    }));
  },

  zoomIn: (spaceId) => {
    set(produce((state: KnowledgeStore) => {
      const c = state.spaces[spaceId];
      if (!c) return;
      c.viewport.zoom = Math.min(3, c.viewport.zoom * 1.25);
    }));
  },

  zoomOut: (spaceId) => {
    set(produce((state: KnowledgeStore) => {
      const c = state.spaces[spaceId];
      if (!c) return;
      c.viewport.zoom = Math.max(0.1, c.viewport.zoom / 1.25);
    }));
  },

  pushUndoState: (spaceId) => {
    const canvas = get().spaces[spaceId];
    if (!canvas) return;
    const snapshot = takeSnapshot(canvas);
    set(produce((state: KnowledgeStore) => {
      state.undoStack.push(snapshot);
      state.redoStack = [];
    }));
  },

  undo: (spaceId) => {
    const state = get();
    const canvas = state.spaces[spaceId];
    if (!canvas || state.undoStack.length === 0) return;
    const current = takeSnapshot(canvas);
    const prev = state.undoStack[state.undoStack.length - 1];
    set(produce((s: KnowledgeStore) => {
      const c = s.spaces[spaceId];
      if (!c) return;
      s.redoStack.push(current);
      s.undoStack.pop();
      c.elements = prev.elements;
    }));
    get().markDirty(spaceId);
  },

  redo: (spaceId) => {
    const state = get();
    const canvas = state.spaces[spaceId];
    if (!canvas || state.redoStack.length === 0) return;
    const current = takeSnapshot(canvas);
    const next = state.redoStack[state.redoStack.length - 1];
    set(produce((s: KnowledgeStore) => {
      const c = s.spaces[spaceId];
      if (!c) return;
      s.undoStack.push(current);
      s.redoStack.pop();
      c.elements = next.elements;
    }));
    get().markDirty(spaceId);
  },

  setArrowStart: (elementId, point) => set({ arrowStart: { elementId, point } }),
  clearArrowStart: () => set({ arrowStart: null }),

  markDirty: (spaceId) => {
    set(produce((state: KnowledgeStore) => {
      state.dirtySpaceIds[spaceId] = true;
      state.lastSavedAt = null;
    }));
  },

  markClean: (spaceId) => {
    set(produce((state: KnowledgeStore) => {
      delete state.dirtySpaceIds[spaceId];
    }));
  },

  setSaving: (saving) => set({ isSaving: saving }),

  getCanvasState: (spaceId) => {
    return get().spaces[spaceId] ?? null;
  },
}));
