'use client';

import { useState, useRef, useEffect } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import {
  MousePointer2,
  Hand,
  Type,
  StickyNote,
  Square,
  ArrowUpRight,
  GitBranch,
  PanelRightOpen,
  PanelRightClose,
  Minus,
  Plus,
  RotateCcw,
  RotateCw,
  Grid3X3,
  Magnet,
  LayoutPanelTop,
  Trash2,
  Circle,
  Triangle,
  Diamond,
  Hexagon,
  ChevronDown,
} from 'lucide-react';
import type { ShapeType } from '@/types/knowledge';

interface Props {
  spaceId: string;
}

const tools = [
  { id: 'select' as const, icon: MousePointer2, label: 'Select (V)' },
  { id: 'hand' as const, icon: Hand, label: 'Hand (H)' },
  { id: 'text' as const, icon: Type, label: 'Text (T)' },
  { id: 'sticky_note' as const, icon: StickyNote, label: 'Sticky Note (N)' },
  { id: 'rectangle' as const, icon: Square, label: 'Shapes (R)' },
  { id: 'arrow' as const, icon: ArrowUpRight, label: 'Arrow (A)' },
  { id: 'flowchart' as const, icon: GitBranch, label: 'Flowchart (F)' },
];

const shapeItems: { id: ShapeType; icon: typeof Square; label: string }[] = [
  { id: 'rectangle', icon: Square, label: 'Rectangle' },
  { id: 'circle', icon: Circle, label: 'Circle' },
  { id: 'triangle', icon: Triangle, label: 'Triangle' },
  { id: 'rhombus', icon: Diamond, label: 'Diamond' },
  { id: 'hexagon', icon: Hexagon, label: 'Hexagon' },
];

const shapeIconMap: Record<ShapeType, typeof Square> = {
  rectangle: Square,
  circle: Circle,
  triangle: Triangle,
  rhombus: Diamond,
  hexagon: Hexagon,
};

export function CanvasToolbar({ spaceId }: Props) {
  const selectedTool = useKnowledgeStore(s => s.selectedTool);
  const subTool = useKnowledgeStore(s => s.subTool);
  const setSelectedTool = useKnowledgeStore(s => s.setSelectedTool);
  const setSubTool = useKnowledgeStore(s => s.setSubTool);
  const showSidebar = useKnowledgeStore(s => s.showSidebar);
  const toggleSidebar = useKnowledgeStore(s => s.toggleSidebar);
  const showMinimap = useKnowledgeStore(s => s.showMinimap);
  const toggleMinimap = useKnowledgeStore(s => s.toggleMinimap);
  const toggleGrid = useKnowledgeStore(s => s.toggleGrid);
  const toggleSnap = useKnowledgeStore(s => s.toggleSnap);
  const zoomIn = useKnowledgeStore(s => s.zoomIn);
  const zoomOut = useKnowledgeStore(s => s.zoomOut);
  const undo = useKnowledgeStore(s => s.undo);
  const redo = useKnowledgeStore(s => s.redo);
  const pushUndoState = useKnowledgeStore(s => s.pushUndoState);
  const deleteSelectedElements = useKnowledgeStore(s => s.deleteSelectedElements);
  const zoom = useKnowledgeStore(s => s.spaces[spaceId]?.viewport.zoom ?? 1);
  const gridOn = useKnowledgeStore(s => s.spaces[spaceId]?.gridEnabled ?? true);
  const snapOn = useKnowledgeStore(s => s.spaces[spaceId]?.snapEnabled ?? true);
  const selectedCount = useKnowledgeStore(s => s.spaces[spaceId]?.selectedElementIds.length ?? 0);

  const [shapeOpen, setShapeOpen] = useState(false);
  const shapeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (shapeRef.current && !shapeRef.current.contains(e.target as Node)) {
        setShapeOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const zoomPercent = Math.round(zoom * 100);
  const hasSelection = selectedCount > 0;
  const ShapeIcon = shapeIconMap[subTool];

  const handleUndo = () => {
    undo(spaceId);
  };

  const handleRedo = () => {
    redo(spaceId);
  };

  const handleDelete = () => {
    pushUndoState(spaceId);
    deleteSelectedElements(spaceId);
  };

  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-50 flex items-center gap-1 px-2 py-1.5 rounded-xl bg-krait-surface2/90 backdrop-blur-md border border-border shadow-lg">
      {tools.map(tool =>
        tool.id === 'rectangle' ? (
          <div key={tool.id} ref={shapeRef} className="relative">
            <button
              onClick={() => {
                setSelectedTool('rectangle');
                setShapeOpen(!shapeOpen);
              }}
              className={`flex items-center gap-0.5 p-1.5 rounded-lg transition-colors ${
                selectedTool === 'rectangle'
                  ? 'bg-venom-yellow/15 text-venom-yellow'
                  : 'text-text-tertiary hover:text-foreground hover:bg-krait-surface3'
              }`}
              title={tool.label}
            >
              <ShapeIcon className="w-4 h-4" />
              <ChevronDown className="w-2.5 h-2.5" />
            </button>
            {shapeOpen && (
              <div className="absolute top-full left-0 mt-1 p-1 rounded-xl bg-krait-surface2/95 backdrop-blur-md border border-border shadow-lg min-w-[140px]">
                {shapeItems.map(item => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        setSubTool(item.id);
                        setSelectedTool('rectangle');
                        setShapeOpen(false);
                      }}
                      className={`flex items-center gap-2 w-full px-2 py-1.5 rounded-lg text-[12px] transition-colors ${
                        subTool === item.id && selectedTool === 'rectangle'
                          ? 'bg-venom-yellow/15 text-venom-yellow'
                          : 'text-text-tertiary hover:text-foreground hover:bg-krait-surface3'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <button
            key={tool.id}
            onClick={() => setSelectedTool(tool.id)}
            className={`p-1.5 rounded-lg transition-colors ${
              selectedTool === tool.id
                ? 'bg-venom-yellow/15 text-venom-yellow'
                : 'text-text-tertiary hover:text-foreground hover:bg-krait-surface3'
            }`}
            title={tool.label}
          >
            <tool.icon className="w-4 h-4" />
          </button>
        )
      )}
      <div className="w-px h-5 bg-border mx-1" />
      <button
        onClick={() => zoomOut(spaceId)}
        className="p-1.5 rounded-lg text-text-tertiary hover:text-foreground hover:bg-krait-surface3"
        title="Zoom out"
      >
        <Minus className="w-4 h-4" />
      </button>
      <span className="text-[11px] text-text-tertiary min-w-[44px] text-center select-none">
        {zoomPercent}%
      </span>
      <button
        onClick={() => zoomIn(spaceId)}
        className="p-1.5 rounded-lg text-text-tertiary hover:text-foreground hover:bg-krait-surface3"
        title="Zoom in"
      >
        <Plus className="w-4 h-4" />
      </button>
      <div className="w-px h-5 bg-border mx-1" />
      <button
        onClick={handleUndo}
        className="p-1.5 rounded-lg text-text-tertiary hover:text-foreground hover:bg-krait-surface3 disabled:opacity-30"
        title="Undo (Ctrl+Z)"
        disabled={useKnowledgeStore.getState().undoStack.length === 0}
      >
        <RotateCcw className="w-4 h-4" />
      </button>
      <button
        onClick={handleRedo}
        className="p-1.5 rounded-lg text-text-tertiary hover:text-foreground hover:bg-krait-surface3 disabled:opacity-30"
        title="Redo (Ctrl+Shift+Z)"
        disabled={useKnowledgeStore.getState().redoStack.length === 0}
      >
        <RotateCw className="w-4 h-4" />
      </button>
      <div className="w-px h-5 bg-border mx-1" />
      <button
        onClick={handleDelete}
        className={`p-1.5 rounded-lg transition-colors ${
          hasSelection
            ? 'text-red-400 hover:bg-red-500/10'
            : 'text-text-tertiary hover:text-foreground hover:bg-krait-surface3'
        }`}
        title="Delete selected (Delete)"
        disabled={!hasSelection}
      >
        <Trash2 className="w-4 h-4" />
      </button>
      <div className="w-px h-5 bg-border mx-1" />
      <button
        onClick={toggleMinimap}
        className={`p-1.5 rounded-lg transition-colors ${
          showMinimap
            ? 'bg-venom-yellow/15 text-venom-yellow'
            : 'text-text-tertiary hover:text-foreground hover:bg-krait-surface3'
        }`}
        title="Toggle minimap"
      >
        <LayoutPanelTop className="w-4 h-4" />
      </button>
      <button
        onClick={() => toggleGrid(spaceId)}
        className={`p-1.5 rounded-lg transition-colors ${
          gridOn
            ? 'bg-venom-yellow/15 text-venom-yellow'
            : 'text-text-tertiary hover:text-foreground hover:bg-krait-surface3'
        }`}
        title="Toggle grid"
      >
        <Grid3X3 className="w-4 h-4" />
      </button>
      <button
        onClick={() => toggleSnap(spaceId)}
        className={`p-1.5 rounded-lg transition-colors ${
          snapOn
            ? 'bg-venom-yellow/15 text-venom-yellow'
            : 'text-text-tertiary hover:text-foreground hover:bg-krait-surface3'
        }`}
        title="Toggle snap"
      >
        <Magnet className="w-4 h-4" />
      </button>
      <div className="w-px h-5 bg-border mx-1" />
      <button
        onClick={toggleSidebar}
        className="p-1.5 rounded-lg text-text-tertiary hover:text-foreground hover:bg-krait-surface3"
        title="Toggle sidebar"
      >
        {showSidebar ? (
          <PanelRightClose className="w-4 h-4" />
        ) : (
          <PanelRightOpen className="w-4 h-4" />
        )}
      </button>
    </div>
  );
}
