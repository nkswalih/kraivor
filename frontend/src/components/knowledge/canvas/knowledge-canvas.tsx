'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import { useCanvasKeyboard } from '@/lib/hooks/use-canvas';
import { CanvasElementRenderer } from '../elements/canvas-element';
import { CanvasToolbar } from './canvas-toolbar';
import { CanvasMinimap } from './canvas-minimap';
import { nanoid } from 'nanoid';
import type { ShapeType, ArrowElementData, Position } from '@/types/knowledge';
import { resolveArrowPoints } from '@/types/knowledge';

function pointToSegmentDist(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const abx = bx - ax;
  const aby = by - ay;
  const len2 = abx * abx + aby * aby;
  if (len2 === 0) return Math.hypot(px - ax, py - ay);
  let t = ((px - ax) * abx + (py - ay) * aby) / len2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (ax + t * abx), py - (ay + t * aby));
}

const SHAPE_DEFAULTS: Record<ShapeType, { width: number; height: number; data: Record<string, unknown> }> = {
  rectangle: { width: 160, height: 100, data: { fillColor: 'transparent', strokeColor: '#cbd5e1', strokeWidth: 2 } },
  circle: { width: 120, height: 120, data: { fillColor: 'transparent', strokeColor: '#cbd5e1', strokeWidth: 2 } },
  triangle: { width: 120, height: 120, data: { fillColor: 'transparent', strokeColor: '#cbd5e1', strokeWidth: 2 } },
  rhombus: { width: 140, height: 100, data: { fillColor: 'transparent', strokeColor: '#cbd5e1', strokeWidth: 2 } },
  hexagon: { width: 140, height: 120, data: { fillColor: 'transparent', strokeColor: '#cbd5e1', strokeWidth: 2 } },
};

interface Props {
  spaceId: string;
}

export function KnowledgeCanvas({ spaceId }: Props) {
  const canvas = useKnowledgeStore(s => s.spaces[spaceId]);
  const selectedTool = useKnowledgeStore(s => s.selectedTool);
  const subTool = useKnowledgeStore(s => s.subTool);
  const editingElementId = useKnowledgeStore(s => s.editingElementId);
  const arrowStart = useKnowledgeStore(s => s.arrowStart);
  const store = useKnowledgeStore;

  const containerRef = useRef<HTMLDivElement>(null);
  const [isPanning, setIsPanning] = useState(false);
  const panRef = useRef({ active: false, startX: 0, startY: 0, startVx: 0, startVy: 0 });
  const dragRef = useRef<{
    elementId: string;
    offsetX: number;
    offsetY: number;
    startPositions: Record<string, Position>;
    startArrowData: Record<string, [number, number][]>;
  }>({ elementId: '', offsetX: 0, offsetY: 0, startPositions: {}, startArrowData: {} });
  const selectionRef = useRef({ started: false, active: false, justSelected: false, startX: 0, startY: 0, endX: 0, endY: 0 });
  const selectionRectRef = useRef<HTMLDivElement | null>(null);
  const resizeRef = useRef({
    elementId: '', startX: 0, startY: 0, startW: 0, startH: 0,
    startPosX: 0, startPosY: 0,
    handlePos: '' as string,
  });
  const createRef = useRef<{ active: boolean; startX: number; startY: number; elementId: string } | null>(null);
  const arrowPointRef = useRef<{
    elementId: string;
    pointType: 'start' | 'end' | 'intermediate' | 'control';
    pointIndex: number;
    startClientX: number;
    startClientY: number;
    points: [number, number][];
    controlPoint: Position | null;
  } | null>(null);

  useCanvasKeyboard(spaceId);

  const getCanvasRect = useCallback(() => {
    return containerRef.current?.getBoundingClientRect() ?? null;
  }, []);

  const screenToWorld = useCallback((clientX: number, clientY: number) => {
    const state = store.getState();
    const c = state.spaces[spaceId];
    const rect = getCanvasRect();
    if (!c || !rect) return null;
    return {
      x: (clientX - rect.left - c.viewport.x) / c.viewport.zoom,
      y: (clientY - rect.top - c.viewport.y) / c.viewport.zoom,
    };
  }, [store, spaceId, getCanvasRect]);

  const findElementAtPoint = useCallback((clientX: number, clientY: number) => {
    const state = store.getState();
    const c = state.spaces[spaceId];
    if (!c) return null;
    const world = screenToWorld(clientX, clientY);
    if (!world) return null;
    const sorted = [...c.elements].sort((a, b) => b.zIndex - a.zIndex);
    for (const el of sorted) {
      if (el.type === 'arrow') {
        const d = el.data as Partial<ArrowElementData>;
        const pts = resolveArrowPoints(d);
        for (let i = 0; i < pts.length - 1; i++) {
          const dist = pointToSegmentDist(world.x, world.y, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]);
          if (dist < 10) return el;
        }
        continue;
      }
      if (
        world.x >= el.position.x && world.x <= el.position.x + el.size.width &&
        world.y >= el.position.y && world.y <= el.position.y + el.size.height
      ) {
        return el;
      }
    }
    return null;
  }, [store, spaceId, screenToWorld]);

  // Window-level mouse handlers
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const state = store.getState();
      const c = state.spaces[spaceId];
      if (!c) return;

      if (panRef.current.active) {
        const dx = e.clientX - panRef.current.startX;
        const dy = e.clientY - panRef.current.startY;
        state.setViewport(spaceId, {
          ...c.viewport,
          x: panRef.current.startVx + dx,
          y: panRef.current.startVy + dy,
        });
        return;
      }

      if (resizeRef.current.elementId) {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        const dw = (e.clientX - resizeRef.current.startX) / c.viewport.zoom;
        const dh = (e.clientY - resizeRef.current.startY) / c.viewport.zoom;
        const startW = resizeRef.current.startW;
        const startH = resizeRef.current.startH;
        const pos = resizeRef.current.handlePos;

        let newW: number, newH: number;
        let dx = 0, dy = 0;

        if (pos === 'e' || pos === 'se' || pos === 'ne') {
          newW = Math.max(30, startW + dw);
        } else if (pos === 'w' || pos === 'sw' || pos === 'nw') {
          newW = Math.max(30, startW - dw);
          dx = startW - newW;
        } else {
          newW = startW;
        }

        if (pos === 's' || pos === 'se' || pos === 'sw') {
          newH = Math.max(20, startH + dh);
        } else if (pos === 'n' || pos === 'ne' || pos === 'nw') {
          newH = Math.max(20, startH - dh);
          dy = startH - newH;
        } else {
          newH = startH;
        }

        const resizeEl = c.elements.find(ee => ee.id === resizeRef.current.elementId);
        if (resizeEl && resizeEl.type === 'arrow') {
          const arrowData: ArrowElementData = JSON.parse(JSON.stringify(resizeEl.data)) as ArrowElementData;
          const arrowPts = resolveArrowPoints(arrowData);
          const scaleX = newW / startW;
          const scaleY = newH / startH;
          const originX = resizeRef.current.startPosX + 40;
          const originY = resizeRef.current.startPosY + 40;
          arrowData.points = arrowPts.map(([px, py]) => [
            originX + (px - originX) * scaleX,
            originY + (py - originY) * scaleY,
          ] as [number, number]);
          state.updateElement(spaceId, resizeRef.current.elementId, {
            position: { x: resizeRef.current.startPosX + dx, y: resizeRef.current.startPosY + dy },
            size: { width: newW, height: newH },
            data: arrowData as unknown as Record<string, unknown>,
          });
        } else {
          state.resizeElement(spaceId, resizeRef.current.elementId, { width: newW, height: newH });
          if (dx !== 0 || dy !== 0) {
            state.moveElement(spaceId, resizeRef.current.elementId, {
              x: resizeRef.current.startPosX + dx,
              y: resizeRef.current.startPosY + dy,
            });
          }
        }
        return;
      }

      if (arrowPointRef.current) {
        const dx = (e.clientX - arrowPointRef.current.startClientX) / c.viewport.zoom;
        const dy = (e.clientY - arrowPointRef.current.startClientY) / c.viewport.zoom;
        const el = c.elements.find(ee => ee.id === arrowPointRef.current!.elementId);
        if (el) {
          const arrowData: ArrowElementData = JSON.parse(JSON.stringify(el.data)) as ArrowElementData;
          const { pointType, pointIndex, points, controlPoint } = arrowPointRef.current;
          if (pointType === 'control') {
            arrowData.controlPoint = {
              x: controlPoint!.x + dx,
              y: controlPoint!.y + dy,
            };
            arrowData.arrowStyle = 'curved';
          } else {
            arrowData.points = points.map((p, i) =>
              i === pointIndex ? [p[0] + dx, p[1] + dy] as [number, number] : [p[0], p[1]] as [number, number]
            );
          }
          const updatedPts = resolveArrowPoints(arrowData);
          const allX = updatedPts.map(p => p[0]);
          const allY = updatedPts.map(p => p[1]);
          const minX = Math.min(...allX) - 40;
          const minY = Math.min(...allY) - 40;
          const maxX = Math.max(...allX) + 40;
          const maxY = Math.max(...allY) + 40;
          state.updateElement(spaceId, el.id, {
            position: { x: minX, y: minY },
            size: { width: maxX - minX, height: maxY - minY },
            data: arrowData as unknown as Record<string, unknown>,
          });
        }
        return;
      }

      if (selectedTool === 'select' && selectionRef.current.started) {
        const world = screenToWorld(e.clientX, e.clientY);
        if (!world) return;
        selectionRef.current.endX = world.x;
        selectionRef.current.endY = world.y;
        const dx = Math.abs(world.x - selectionRef.current.startX);
        const dy = Math.abs(world.y - selectionRef.current.startY);
        if (dx > 3 || dy > 3) {
          selectionRef.current.active = true;
        }
        if (selectionRef.current.active) {
          const el = selectionRectRef.current;
          if (el) {
            const left = Math.min(selectionRef.current.startX, world.x);
            const top = Math.min(selectionRef.current.startY, world.y);
            el.style.display = 'block';
            el.style.left = left + 'px';
            el.style.top = top + 'px';
            el.style.width = Math.abs(world.x - selectionRef.current.startX) + 'px';
            el.style.height = Math.abs(world.y - selectionRef.current.startY) + 'px';
          }
        }
        return;
      }

      if (dragRef.current.elementId) {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        const startPositions = dragRef.current.startPositions;
        const keys = Object.keys(startPositions);
        const totalDx = ((e.clientX - rect.left - c.viewport.x) / c.viewport.zoom - dragRef.current.offsetX) - startPositions[dragRef.current.elementId].x;
        const totalDy = ((e.clientY - rect.top - c.viewport.y) / c.viewport.zoom - dragRef.current.offsetY) - startPositions[dragRef.current.elementId].y;
        if (totalDx === 0 && totalDy === 0) return;
        for (const id of keys) {
          const sp = startPositions[id];
          const other = c.elements.find(ee => ee.id === id);
          if (!other) continue;
          if (other.type === 'arrow') {
            const srcPts = dragRef.current.startArrowData[id];
            if (!srcPts) continue;
            const otherData = other.data as Record<string, unknown>;
            const nd: Record<string, unknown> = { ...otherData, points: srcPts.map(([px, py]) => [px + totalDx, py + totalDy] as [number, number]) };
            if (otherData.controlPoint) {
              const cp = otherData.controlPoint as Position;
              nd.controlPoint = { x: cp.x + totalDx, y: cp.y + totalDy };
            }
            state.updateElement(spaceId, id, {
              position: { x: sp.x + totalDx, y: sp.y + totalDy },
              data: nd,
            });
          } else {
            state.moveElement(spaceId, id, { x: sp.x + totalDx, y: sp.y + totalDy });
          }
        }
        return;
      }

      if (createRef.current?.active) {
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;
        const worldX = (e.clientX - rect.left - c.viewport.x) / c.viewport.zoom;
        const worldY = (e.clientY - rect.top - c.viewport.y) / c.viewport.zoom;
        const cr = createRef.current;
        const sx = cr.startX;
        const sy = cr.startY;
        const el = c.elements.find(ee => ee.id === cr.elementId);
        if (el && el.type === 'arrow') {
          const arrowData: ArrowElementData = JSON.parse(JSON.stringify(el.data)) as ArrowElementData;
          arrowData.points = [[sx, sy], [worldX, worldY]];
          const allX = [sx, worldX];
          const allY = [sy, worldY];
          const minX = Math.min(...allX) - 40;
          const minY = Math.min(...allY) - 40;
          const maxX = Math.max(...allX) + 40;
          const maxY = Math.max(...allY) + 40;
          state.updateElement(spaceId, createRef.current.elementId, {
            position: { x: minX, y: minY },
            size: { width: maxX - minX, height: maxY - minY },
            data: arrowData as unknown as Record<string, unknown>,
          });
        } else {
          const x = Math.min(sx, worldX);
          const y = Math.min(sy, worldY);
          const w = Math.max(30, Math.abs(worldX - sx));
          const h = Math.max(20, Math.abs(worldY - sy));
          state.updateElement(spaceId, createRef.current.elementId, { position: { x, y }, size: { width: w, height: h } });
        }
        return;
      }
    };

    const handleMouseUp = (e: MouseEvent) => {
      const state = store.getState();
      const c = state.spaces[spaceId];
      panRef.current.active = false;
      setIsPanning(false);
      // Capture and clear selection state early so it doesn't block other
      // branches (dragRef etc.) if there's a stale previous interaction
      const wasSelectionStarted = selectionRef.current.started;
      const wasSelectionActive = selectionRef.current.active;
      selectionRef.current.started = false;
      selectionRef.current.active = false;
      if (selectionRectRef.current) selectionRectRef.current.style.display = 'none';

      if (resizeRef.current.elementId) {
        const id = resizeRef.current.elementId;
        dragRef.current.elementId = '';
        resizeRef.current.elementId = '';
        if (!c?.selectedElementIds.includes(id)) {
          state.setSelectedElements(spaceId, [id]);
        }
        return;
      }

      if (dragRef.current.elementId) {
        const id = dragRef.current.elementId;
        dragRef.current.elementId = '';
        if (!e.shiftKey && !c?.selectedElementIds.includes(id)) {
          state.setSelectedElements(spaceId, [id]);
        }
        return;
      }

      if (arrowPointRef.current) {
        const id = arrowPointRef.current.elementId;
        arrowPointRef.current = null;
        if (!c?.selectedElementIds.includes(id)) {
          state.setSelectedElements(spaceId, [id]);
        }
        return;
      }

      if (createRef.current?.active && c) {
        const eid = createRef.current.elementId;
        const tempEl = c.elements.find(ee => ee.id === eid);
        if (tempEl && (tempEl.size.width < 5 || tempEl.size.height < 5)) {
          state.removeElement(spaceId, eid);
        }
        createRef.current = null;
        state.setSelectedTool('select');
        return;
      }

      if (wasSelectionStarted) {
        if (wasSelectionActive && c) {
          const s = selectionRef.current;
          const rx = Math.min(s.startX, s.endX);
          const ry = Math.min(s.startY, s.endY);
          const rw = Math.abs(s.endX - s.startX);
          const rh = Math.abs(s.endY - s.startY);
          const selected = c.elements.filter(el =>
            el.position.x < rx + rw &&
            el.position.x + el.size.width > rx &&
            el.position.y < ry + rh &&
            el.position.y + el.size.height > ry
          ).map(el => el.id);
          state.setSelectedElements(spaceId, selected);
          selectionRef.current.justSelected = true;
        }
        return;
      }

      if (selectedTool === 'arrow' && arrowStart) {
        const target = findElementAtPoint(e.clientX, e.clientY);
        if (target) {
          const startWorld = screenToWorld(e.clientX, e.clientY);
          if (startWorld) {
            const sx = arrowStart.point.x;
            const sy = arrowStart.point.y;
            const ex = target.position.x + target.size.width / 2;
            const ey = target.position.y + target.size.height / 2;
            const midX = (sx + ex) / 2;
            const distX = Math.abs(ex - sx);
            const midY = distX > 100 ? sy : (sy + ey) / 2;
            const pts: [number, number][] = [[sx, sy], [midX, midY], [ex, ey]];
            const allX = pts.map(p => p[0]);
            const allY = pts.map(p => p[1]);
            const minX = Math.min(...allX);
            const minY = Math.min(...allY);
            const maxX = Math.max(...allX);
            const maxY = Math.max(...allY);
            const pad = 40;
            state.addElement(spaceId, 'arrow', { x: minX - pad, y: minY - pad }, { width: maxX - minX + pad * 2, height: maxY - minY + pad * 2 }, {
              startElementId: arrowStart.elementId,
              endElementId: target.id,
              points: pts,
              controlPoint: { x: midX, y: (sy + ey) / 2 },
              arrowStyle: 'curved',
              color: '#e2e8f0',
              lineWidth: 2,
            } as unknown as Record<string, unknown>);
          }
        }
        state.clearArrowStart();
        return;
      }

      dragRef.current.elementId = '';
      resizeRef.current.elementId = '';
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      selectionRef.current.started = false;
      selectionRef.current.active = false;
      if (selectionRectRef.current) selectionRectRef.current.style.display = 'none';
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [store, spaceId, selectedTool, arrowStart, findElementAtPoint, screenToWorld]);

  const handleCanvasClick = () => {
    if (createRef.current?.active) return;
    if (selectionRef.current.justSelected) {
      selectionRef.current.justSelected = false;
      return;
    }
    const state = store.getState();
    const c = state.spaces[spaceId];
    state.setSelectedElements(spaceId, []);
    if (arrowStart) {
      state.clearArrowStart();
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const state = store.getState();
    const c = state.spaces[spaceId];

    if (selectedTool === 'hand' || e.button === 1) {
      panRef.current = {
        active: true,
        startX: e.clientX,
        startY: e.clientY,
        startVx: c?.viewport.x ?? 0,
        startVy: c?.viewport.y ?? 0,
      };
      setIsPanning(true);
      e.preventDefault();
      return;
    }

    if (selectedTool === 'arrow') {
      const world = screenToWorld(e.clientX, e.clientY);
      if (!world) return;
      state.pushUndoState(spaceId);
      const sx = world.x;
      const sy = world.y;
      const pts: [number, number][] = [[sx, sy], [sx + 50, sy]];
      const allX = [sx, sx + 50];
      const allY = [sy, sy];
      const minX = Math.min(...allX) - 40;
      const minY = Math.min(...allY) - 40;
      const maxX = Math.max(...allX) + 40;
      const maxY = Math.max(...allY) + 40;
      const id = state.addElement(spaceId, 'arrow', { x: minX, y: minY }, { width: maxX - minX, height: maxY - minY }, {
        points: pts,
        arrowStyle: 'straight',
        color: '#e2e8f0',
        lineWidth: 2,
      } as unknown as Record<string, unknown>);
      createRef.current = { active: true, startX: sx, startY: sy, elementId: id };
      state.setEditingElementId(null);
      e.preventDefault();
      return;
    }

    if (selectedTool === 'flowchart') {
      const world = screenToWorld(e.clientX, e.clientY);
      if (!world) return;
      const cx = world.x;
      const cy = world.y;

      const nw = 140;
      const gap = 20;
      const nodeH: Record<string, number> = { 'start-node': 50, 'process-node': 60, 'decision-node': 80, 'end-node': 50 };

      const flowNodes = [
        { type: 'start-node' as const, label: 'Start', yOff: 0, h: 50 },
        { type: 'process-node' as const, label: 'Process Task', yOff: 50 + gap, h: 60 },
        { type: 'decision-node' as const, label: 'Decision?', yOff: 50 + gap + 60 + gap, h: 80 },
        { type: 'end-node' as const, label: 'End', yOff: 50 + gap + 60 + gap + 80 + gap, h: 50 },
      ];

      state.pushUndoState(spaceId);
      const nodeIds: string[] = [];

      for (const n of flowNodes) {
        const y = cy - 25 + n.yOff;
        const id = state.addElement(spaceId, n.type, { x: cx - nw / 2, y }, { width: nw, height: n.h }, {
          label: n.label,
        });
        nodeIds.push(id);
      }

      function addArrowBetween(srcIdx: number, tgtIdx: number, label?: string) {
        const srcEl = store.getState().spaces[spaceId]?.elements.find(e => e.id === nodeIds[srcIdx]);
        const tgtEl = store.getState().spaces[spaceId]?.elements.find(e => e.id === nodeIds[tgtIdx]);
        if (!srcEl || !tgtEl) return;
        const sx = srcEl.position.x + srcEl.size.width / 2;
        const sy = srcEl.position.y + srcEl.size.height;
        const ex = tgtEl.position.x + tgtEl.size.width / 2;
        const ey = tgtEl.position.y;
        const midX = (sx + ex) / 2;
        const pts: [number, number][] = [[sx, sy], [midX, (sy + ey) / 2], [ex, ey]];
        const allX = pts.map(p => p[0]);
        const allY = pts.map(p => p[1]);
        const minX = Math.min(...allX);
        const minY = Math.min(...allY);
        const maxX = Math.max(...allX);
        const maxY = Math.max(...allY);
        const pad = 40;
        state.addElement(spaceId, 'arrow', { x: minX - pad, y: minY - pad }, { width: maxX - minX + pad * 2, height: maxY - minY + pad * 2 }, {
          startElementId: nodeIds[srcIdx],
          endElementId: nodeIds[tgtIdx],
          points: pts,
          controlPoint: { x: midX, y: (sy + ey) / 2 },
          arrowStyle: 'curved',
          color: '#e2e8f0',
          lineWidth: 2,
        } as unknown as Record<string, unknown>);
      }

      addArrowBetween(0, 1);
      addArrowBetween(1, 2);
      addArrowBetween(2, 3, 'Yes');

      state.setEditingElementId(null);
      state.setSelectedTool('select');
      e.preventDefault();
      return;
    }

    if (selectedTool === 'rectangle') {
      const world = screenToWorld(e.clientX, e.clientY);
      if (!world) return;
      const defaults = SHAPE_DEFAULTS[subTool] ?? SHAPE_DEFAULTS.rectangle;
      state.pushUndoState(spaceId);
      const id = state.addElement(spaceId, subTool, { x: world.x, y: world.y }, { width: 1, height: 1 }, defaults.data);
      createRef.current = { active: true, startX: world.x, startY: world.y, elementId: id };
      state.setEditingElementId(null);
      e.preventDefault();
      return;
    }

    if (selectedTool === 'select') {
      if (findElementAtPoint(e.clientX, e.clientY)) return;
      const world = screenToWorld(e.clientX, e.clientY);
      if (!world) return;
      if (selectionRectRef.current) selectionRectRef.current.style.display = 'none';
      selectionRef.current = { started: true, active: false, justSelected: false, startX: world.x, startY: world.y, endX: world.x, endY: world.y };
      e.preventDefault();
      return;
    }
  };

  const handleWheel = (e: WheelEvent) => {
    e.preventDefault();
    const state = store.getState();
    const c = state.spaces[spaceId];
    if (!c) return;
    const delta = -e.deltaY * 0.001;
    const newZoom = Math.max(0.1, Math.min(3, c.viewport.zoom * (1 + delta)));
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const worldX = (mx - c.viewport.x) / c.viewport.zoom;
    const worldY = (my - c.viewport.y) / c.viewport.zoom;
    state.setViewport(spaceId, {
      x: mx - worldX * newZoom,
      y: my - worldY * newZoom,
      zoom: newZoom,
    });
  };

  const wheelRef = useRef(handleWheel);
  wheelRef.current = handleWheel;
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = (e: WheelEvent) => wheelRef.current(e);
    el.addEventListener('wheel', handler, { passive: false });
    return () => el.removeEventListener('wheel', handler);
  }, []);

  const handleElementDragStart = (e: React.MouseEvent, elementId: string) => {
    e.stopPropagation();
    const state = store.getState();
    const c = state.spaces[spaceId];
    if (!c) return;
    const el = c.elements.find(ee => ee.id === elementId);
    if (!el || el.locked) return;

    if (selectedTool === 'arrow') {
      const world = screenToWorld(e.clientX, e.clientY);
      if (!world) return;
      const centerX = el.position.x + el.size.width / 2;
      const centerY = el.position.y + el.size.height / 2;
      state.setArrowStart(elementId, { x: centerX, y: centerY });
      return;
    }

    if (!e.shiftKey && !c.selectedElementIds.includes(elementId)) {
      state.setSelectedElements(spaceId, [elementId]);
    }

    state.pushUndoState(spaceId);
    state.setEditingElementId(null);
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const worldX = (e.clientX - rect.left - c.viewport.x) / c.viewport.zoom;
    const worldY = (e.clientY - rect.top - c.viewport.y) / c.viewport.zoom;

    const selectedIds = c.selectedElementIds.length > 0 ? c.selectedElementIds : [elementId];
    const startPositions: Record<string, Position> = {};
    const startArrowData: Record<string, [number, number][]> = {};
    for (const id of selectedIds) {
      const selEl = c.elements.find(ee => ee.id === id);
      if (!selEl) continue;
      startPositions[id] = { x: selEl.position.x, y: selEl.position.y };
      if (selEl.type === 'arrow') {
        const pts = (selEl.data as Record<string, unknown>).points as [number, number][] | undefined;
        if (pts) startArrowData[id] = pts.map(p => [p[0], p[1]]);
      }
    }
    dragRef.current = {
      elementId,
      offsetX: worldX - el.position.x,
      offsetY: worldY - el.position.y,
      startPositions,
      startArrowData,
    };
  };

  const handleElementResizeStart = (e: React.MouseEvent, elementId: string) => {
    e.stopPropagation();
    e.preventDefault();
    const state = store.getState();
    const c = state.spaces[spaceId];
    if (!c) return;
    const el = c.elements.find(ee => ee.id === elementId);
    if (!el || el.locked) return;
    state.pushUndoState(spaceId);
    const target = e.target as HTMLElement;
    const pos = target.dataset.handlePos ?? 'se';
    resizeRef.current = {
      elementId,
      startX: e.clientX,
      startY: e.clientY,
      startW: el.size.width,
      startH: el.size.height,
      startPosX: el.position.x,
      startPosY: el.position.y,
      handlePos: pos,
    };
    state.setEditingElementId(null);
  };

  const handleArrowPointDragStart = (e: React.MouseEvent, elementId: string, pointType: 'start' | 'end' | 'intermediate' | 'control', pointIndex: number) => {
    e.stopPropagation();
    e.preventDefault();
    const state = store.getState();
    const c = state.spaces[spaceId];
    if (!c) return;
    const el = c.elements.find(ee => ee.id === elementId);
    if (!el) return;
    const arrowData = el.data as Partial<ArrowElementData>;
    const pts = resolveArrowPoints(arrowData);
    state.pushUndoState(spaceId);
    let cp = arrowData.controlPoint ? { ...arrowData.controlPoint } : null;
    if (pointType === 'control' && !cp) {
      const first = pts[0];
      const last = pts[pts.length - 1];
      cp = { x: (first[0] + last[0]) / 2, y: (first[1] + last[1]) / 2 };
    }
    arrowPointRef.current = {
      elementId,
      pointType,
      pointIndex,
      startClientX: e.clientX,
      startClientY: e.clientY,
      points: pts.map(([x, y]) => [x, y] as [number, number]),
      controlPoint: cp,
    };
  };

  const handleElementSelect = (elementId: string, multi: boolean) => {
    const state = store.getState();
    const c = state.spaces[spaceId];
    if (!c) return;
    if (!multi) {
      state.setEditingElementId(null);
    }
    if (multi) {
      const current = c.selectedElementIds;
      const next = current.includes(elementId)
        ? current.filter(id => id !== elementId)
        : [...current, elementId];
      state.setSelectedElements(spaceId, next);
    } else {
      state.setSelectedElements(spaceId, [elementId]);
    }
  };

  const handleElementDoubleClick = (elementId: string) => {
    const state = store.getState();
    const c = state.spaces[spaceId];
    if (!c) return;
    const el = c.elements.find(ee => ee.id === elementId);
    if (!el || el.locked) return;
    if (el.type === 'text' || el.type === 'sticky_note' || el.type === 'markdown') {
      state.setEditingElementId(elementId);
      state.setSelectedElements(spaceId, [elementId]);
    }
  };

  const handleCanvasDoubleClick = (e: React.MouseEvent) => {
    const state = store.getState();
    const c = state.spaces[spaceId];
    if (!c) return;
    if (!containerRef.current) return;

    // Don't create text when double-clicking on an element
    if (findElementAtPoint(e.clientX, e.clientY)) return;

    const rect = containerRef.current.getBoundingClientRect();
    const worldX = (e.clientX - rect.left - c.viewport.x) / c.viewport.zoom;
    const worldY = (e.clientY - rect.top - c.viewport.y) / c.viewport.zoom;

    if (selectedTool === 'text') {
      const id = state.addElement(spaceId, 'text', { x: worldX, y: worldY }, { width: 240, height: 80 }, {
        text: 'Edit me',
        fontSize: 14,
        fontWeight: 'normal',
        fontFamily: 'inherit',
        color: '#e2e8f0',
        backgroundColor: null,
        textAlign: 'left',
        padding: 12,
      });
      state.setEditingElementId(id);
      state.setSelectedTool('select');
    } else if (selectedTool === 'sticky_note') {
      state.addElement(spaceId, 'sticky_note', { x: worldX, y: worldY }, { width: 200, height: 200 }, {
        text: 'New note',
        color: '#fef08a',
        fontSize: 14,
      });
      state.setSelectedTool('select');
    } else {
      const id = state.addElement(spaceId, 'text', { x: worldX, y: worldY }, { width: 240, height: 80 }, {
        text: 'Edit me',
        fontSize: 14,
        fontWeight: 'normal',
        fontFamily: 'inherit',
        color: '#e2e8f0',
        backgroundColor: null,
        textAlign: 'left',
        padding: 12,
      });
      state.setEditingElementId(id);
    }
  };

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const state = store.getState();
      switch (e.key.toLowerCase()) {
        case 'v': state.setSelectedTool('select'); break;
        case 'h': state.setSelectedTool('hand'); break;
        case 't': state.setSelectedTool('text'); break;
        case 'n': state.setSelectedTool('sticky_note'); break;
        case 'r': state.setSelectedTool('rectangle'); break;
        case 'a': state.setSelectedTool('arrow'); break;
        case 'f': state.setSelectedTool('flowchart'); break;
        case 'Escape':
          if (arrowStart) state.clearArrowStart();
          state.setEditingElementId(null);
          break;
      }
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [store, arrowStart]);

  const sortedElements = canvas ? [...canvas.elements].sort((a, b) => a.zIndex - b.zIndex) : [];
  const viewport = canvas?.viewport ?? { x: 0, y: 0, zoom: 1 };
  const gridEnabled = canvas?.gridEnabled ?? true;
  const gridSize = canvas?.gridSize ?? 20;

  return (
    <div className="relative flex-1 overflow-hidden bg-krait-void">
      <CanvasToolbar spaceId={spaceId} />

      <div
        ref={containerRef}
        className={`absolute inset-0 ${
          isPanning ? 'cursor-grabbing' :
          selectedTool === 'hand' ? 'cursor-grab' :
          selectedTool !== 'select' ? 'cursor-crosshair' :
          'cursor-default'
        }`}
        style={{
          backgroundImage: gridEnabled
            ? `radial-gradient(circle, var(--krait-border) 1px, transparent 1px)`
            : undefined,
          backgroundSize: `${gridSize * viewport.zoom}px ${gridSize * viewport.zoom}px`,
          backgroundPosition: `${viewport.x}px ${viewport.y}px`,
        }}
        onClick={handleCanvasClick}
        onDoubleClick={handleCanvasDoubleClick}
        onMouseDown={handleMouseDown}
      >
        <div
          style={{
            transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`,
            transformOrigin: '0 0',
            width: 0,
            height: 0,
          }}
        >
          {sortedElements.map(element => (
            <CanvasElementRenderer
              key={element.id}
              element={element}
              spaceId={spaceId}
              isSelected={canvas?.selectedElementIds.includes(element.id) ?? false}
              isEditing={editingElementId === element.id}
              onSelect={handleElementSelect}
              onDragStart={handleElementDragStart}
              onResizeStart={handleElementResizeStart}
              onArrowPointDragStart={handleArrowPointDragStart}
              onDoubleClick={handleElementDoubleClick}
              onEditEnd={() => {
                const state = store.getState();
                const id = state.editingElementId;
                if (id) {
                  const el = state.spaces[spaceId]?.elements.find(e => e.id === id);
                  if (el && el.type === 'text') {
                    const textData = el.data as { text?: string };
                    if (!textData.text || textData.text === 'Edit me') {
                      state.removeElement(spaceId, id);
                    }
                  }
                }
                state.setEditingElementId(null);
              }}
            />
          ))}

          <div
            ref={selectionRectRef}
            className="absolute pointer-events-none"
            style={{
              display: 'none',
              border: '1.5px solid #eab308',
              backgroundColor: 'rgba(234, 179, 8, 0.15)',
              zIndex: 9999,
            }}
          />
        </div>
      </div>

      <CanvasMinimap spaceId={spaceId} />
    </div>
  );
}
