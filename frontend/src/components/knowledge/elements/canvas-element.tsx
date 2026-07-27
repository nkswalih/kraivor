'use client';

import { memo, useMemo } from 'react';
import dynamic from 'next/dynamic';
import type {
  CanvasElement,
  ArrowElementData,
  ShapeElementData,
  Position,
} from '@/types/knowledge';
import { resolveArrowPoints } from '@/types/knowledge';
import { TextElement } from './text-element';
import { MarkdownElement } from './markdown-element';
import { CodeElement } from './code-element';
import { ImageElement } from './image-element';
import { StickyNoteElement } from './sticky-note-element';

const PdfElement = dynamic(
  () => import('./pdf-element').then(m => m.PdfElement),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full bg-krait-surface3 flex items-center justify-center">
        <span className="text-[12px] text-text-tertiary">Loading PDF...</span>
      </div>
    ),
  },
);

interface Props {
  element: CanvasElement;
  spaceId: string;
  isSelected: boolean;
  isEditing: boolean;
  selectedTool: string;
  onSelect: (id: string, multi: boolean) => void;
  onDragStart: (e: React.MouseEvent, id: string) => void;
  onResizeStart: (e: React.MouseEvent, id: string) => void;
  onArrowPointDragStart: (
    e: React.MouseEvent,
    elementId: string,
    pointType: 'start' | 'end' | 'intermediate' | 'control',
    pointIndex: number
  ) => void;
  onDoubleClick: (id: string) => void;
  onEditEnd: () => void;
}

const HANDLE_SIZE = 8;
const handlePositions = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'] as const;
const SHAPE_TYPES = new Set(['rectangle', 'circle', 'triangle', 'rhombus', 'hexagon']);
const FLOWCHART_NODE_TYPES = new Set(['start-node', 'process-node', 'decision-node', 'end-node']);

function getHandleStyle(pos: (typeof handlePositions)[number], w: number, h: number) {
  const half = HANDLE_SIZE / 2;
  switch (pos) {
    case 'nw':
      return { top: -half, left: -half, cursor: 'nwse-resize' };
    case 'n':
      return { top: -half, left: w / 2 - half, cursor: 'ns-resize' };
    case 'ne':
      return { top: -half, left: w - half, cursor: 'nesw-resize' };
    case 'e':
      return { top: h / 2 - half, left: w - half, cursor: 'ew-resize' };
    case 'se':
      return { top: h - half, left: w - half, cursor: 'nwse-resize' };
    case 's':
      return { top: h - half, left: w / 2 - half, cursor: 'ns-resize' };
    case 'sw':
      return { top: h - half, left: -half, cursor: 'nesw-resize' };
    case 'w':
      return { top: h / 2 - half, left: -half, cursor: 'ew-resize' };
  }
}

function renderContent(
  type: CanvasElement['type'],
  data: Record<string, unknown>,
  elementId: string,
  spaceId: string,
  isEditing: boolean,
  onEditEnd: () => void
) {
  switch (type) {
    case 'text':
      return (
        <TextElement
          data={data as never}
          elementId={elementId}
          spaceId={spaceId}
          isEditing={isEditing}
          onEditEnd={onEditEnd}
        />
      );
    case 'markdown':
      return <MarkdownElement data={data as never} />;
    case 'code':
      return <CodeElement data={data as never} />;
    case 'image':
      return <ImageElement data={data as never} />;
    case 'pdf':
      return <PdfElement data={data as never} />;
    case 'sticky_note':
      return (
        <StickyNoteElement
          data={data as never}
          elementId={elementId}
          spaceId={spaceId}
          isEditing={isEditing}
          onEditEnd={onEditEnd}
        />
      );
    default:
      return (
        <div className="flex items-center justify-center h-full text-text-tertiary text-[13px]">
          {type}
        </div>
      );
  }
}

function ShapeSvg({
  type,
  w,
  h,
  data,
}: {
  type: string;
  w: number;
  h: number;
  data: Record<string, unknown>;
}) {
  const shapeData = data as Partial<ShapeElementData>;
  const fill = shapeData.fillColor ?? 'transparent';
  const stroke = shapeData.strokeColor ?? '#cbd5e1';
  const strokeWidth = Math.max(1, shapeData.strokeWidth ?? 2);

  switch (type) {
    case 'rectangle':
      return (
        <svg width={w} height={h}>
          <rect
            x={strokeWidth / 2}
            y={strokeWidth / 2}
            width={w - strokeWidth}
            height={h - strokeWidth}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
            rx={4}
          />
        </svg>
      );
    case 'circle':
      return (
        <svg width={w} height={h}>
          <ellipse
            cx={w / 2}
            cy={h / 2}
            rx={Math.max(1, w / 2 - strokeWidth)}
            ry={Math.max(1, h / 2 - strokeWidth)}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
        </svg>
      );
    case 'triangle':
      return (
        <svg width={w} height={h}>
          <polygon
            points={`${w / 2},${strokeWidth} ${w - strokeWidth},${h - strokeWidth} ${strokeWidth},${h - strokeWidth}`}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'rhombus':
      return (
        <svg width={w} height={h}>
          <polygon
            points={`${w / 2},${strokeWidth} ${w - strokeWidth},${h / 2} ${w / 2},${h - strokeWidth} ${strokeWidth},${h / 2}`}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeLinejoin="round"
          />
        </svg>
      );
    case 'hexagon':
      return (
        <svg width={w} height={h}>
          <polygon
            points={`${w * 0.25},${strokeWidth} ${w * 0.75},${strokeWidth} ${w - strokeWidth},${h / 2} ${w * 0.75},${h - strokeWidth} ${w * 0.25},${h - strokeWidth} ${strokeWidth},${h / 2}`}
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeLinejoin="round"
          />
        </svg>
      );
    default:
      return null;
  }
}

const FLOWCHART_NODE_COLORS: Record<string, { fill: string; stroke: string }> = {
  'start-node': { fill: '#86efac', stroke: '#4ade80' },
  'process-node': { fill: '#93c5fd', stroke: '#60a5fa' },
  'decision-node': { fill: '#fde68a', stroke: '#fbbf24' },
  'end-node': { fill: '#fca5a5', stroke: '#f87171' },
};

function FlowchartNodeSvg({
  type,
  w,
  h,
  data,
}: {
  type: string;
  w: number;
  h: number;
  data: Record<string, unknown>;
}) {
  const nodeData = data as Partial<{ label: string; fillColor: string; strokeColor: string }>;
  const colors = FLOWCHART_NODE_COLORS[type] ?? { fill: '#93c5fd', stroke: '#60a5fa' };
  const fill = nodeData.fillColor ?? colors.fill;
  const stroke = nodeData.strokeColor ?? colors.stroke;
  const label =
    nodeData.label ??
    (type === 'start-node'
      ? 'Start'
      : type === 'process-node'
        ? 'Process'
        : type === 'decision-node'
          ? 'Decision'
          : 'End');
  const sw = 2;

  const shape = (() => {
    switch (type) {
      case 'start-node':
      case 'end-node':
        return (
          <rect
            x={sw / 2}
            y={sw / 2}
            width={w - sw}
            height={h - sw}
            rx={20}
            fill={fill}
            stroke={stroke}
            strokeWidth={sw}
          />
        );
      case 'process-node':
        return (
          <rect
            x={sw / 2}
            y={sw / 2}
            width={w - sw}
            height={h - sw}
            rx={6}
            fill={fill}
            stroke={stroke}
            strokeWidth={sw}
          />
        );
      case 'decision-node':
        return (
          <polygon
            points={`${w / 2},${sw} ${w - sw},${h / 2} ${w / 2},${h - sw} ${sw},${h / 2}`}
            fill={fill}
            stroke={stroke}
            strokeWidth={sw}
            strokeLinejoin="round"
          />
        );
      default:
        return (
          <rect
            x={sw / 2}
            y={sw / 2}
            width={w - sw}
            height={h - sw}
            rx={6}
            fill={fill}
            stroke={stroke}
            strokeWidth={sw}
          />
        );
    }
  })();

  return (
    <svg width={w} height={h} className="overflow-visible">
      <g>
        {shape}
        <text
          x={w / 2}
          y={h / 2}
          textAnchor="middle"
          dominantBaseline="central"
          fill="#1c1917"
          fontSize={13}
          fontFamily="Inter, system-ui, sans-serif"
          fontWeight={600}
        >
          {label}
        </text>
      </g>
    </svg>
  );
}

function ArrowSvg({
  element,
  isSelected,
  onPointDragStart,
  offsetX,
  offsetY,
  width,
  height,
}: {
  element: CanvasElement;
  isSelected: boolean;
  onPointDragStart: (
    e: React.MouseEvent,
    elementId: string,
    pointType: 'start' | 'end' | 'intermediate' | 'control',
    pointIndex: number
  ) => void;
  offsetX: number;
  offsetY: number;
  width: number;
  height: number;
}) {
  const d = element.data as Partial<ArrowElementData>;
  const pts = useMemo(
    () => resolveArrowPoints(d).map(([x, y]) => [x - offsetX, y - offsetY] as [number, number]),
    [d, offsetX, offsetY]
  );
  const color = d.color ?? '#e2e8f0';
  const lw = d.lineWidth ?? 2;
  const style = d.arrowStyle ?? 'straight';
  const cp = d.controlPoint
    ? { x: d.controlPoint.x - offsetX, y: d.controlPoint.y - offsetY }
    : null;

  const path = useMemo(() => {
    if (pts.length < 2) return '';
    if (style === 'curved' && cp) {
      let d = `M ${pts[0][0]} ${pts[0][1]}`;
      for (let i = 1; i < pts.length; i++) {
        d += ` Q ${cp.x} ${cp.y} ${pts[i][0]} ${pts[i][1]}`;
      }
      return d;
    }
    return pts.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(' ');
  }, [pts, style, cp]);

  const arrowLen = 10;
  const last = pts[pts.length - 1];
  const prev = pts.length >= 2 ? pts[pts.length - 2] : [last[0] - 1, last[1]];

  let angle: number;
  if (style === 'curved' && cp) {
    angle = Math.atan2(last[1] - cp.y, last[0] - cp.x);
  } else {
    angle = Math.atan2(last[1] - prev[1], last[0] - prev[0]);
  }
  const ax = last[0] - arrowLen * Math.cos(angle - Math.PI / 6);
  const ay = last[1] - arrowLen * Math.sin(angle - Math.PI / 6);
  const bx = last[0] - arrowLen * Math.cos(angle + Math.PI / 6);
  const by = last[1] - arrowLen * Math.sin(angle + Math.PI / 6);

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ pointerEvents: 'auto', overflow: 'visible' }}
    >
      <path
        d={path}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={lw}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polygon
        points={`${last[0]},${last[1]} ${ax},${ay} ${bx},${by}`}
        fill={color}
        stroke={color}
        strokeWidth={1}
        strokeLinejoin="round"
      />

      {isSelected && (
        <>
          <rect
            x={2}
            y={2}
            width={Math.max(0, width - 4)}
            height={Math.max(0, height - 4)}
            fill="none"
            stroke="#eab308"
            strokeWidth={2}
            rx={6}
            strokeDasharray="4 3"
            pointerEvents="none"
          />

          {pts.map((p, i) => (
            <circle
              key={i}
              cx={p[0]}
              cy={p[1]}
              r={5}
              fill="white"
              stroke="#eab308"
              strokeWidth={2}
              style={{ cursor: 'move' }}
              onMouseDown={e => {
                e.stopPropagation();
                const ptType = i === 0 ? 'start' : i === pts.length - 1 ? 'end' : 'intermediate';
                onPointDragStart(e as unknown as React.MouseEvent, element.id, ptType, i);
              }}
            />
          ))}

          {(() => {
            const first = pts[0];
            const last = pts[pts.length - 1];
            const cx = cp?.x ?? (first[0] + last[0]) / 2;
            const cy = cp?.y ?? (first[1] + last[1]) / 2;
            return (
              <circle
                cx={cx}
                cy={cy}
                r={4}
                fill="#eab308"
                stroke="white"
                strokeWidth={1.5}
                style={{ cursor: 'grab' }}
                onMouseDown={e => {
                  e.stopPropagation();
                  onPointDragStart(e as unknown as React.MouseEvent, element.id, 'control', -1);
                }}
              />
            );
          })()}
        </>
      )}
    </svg>
  );
}

function canvasElementAreEqual(prev: Props, next: Props): boolean {
  if (prev.isSelected !== next.isSelected) return false;
  if (prev.isEditing !== next.isEditing) return false;
  if (prev.selectedTool !== next.selectedTool) return false;
  const a = prev.element;
  const b = next.element;
  return (
    a.id === b.id &&
    a.position.x === b.position.x &&
    a.position.y === b.position.y &&
    a.size.width === b.size.width &&
    a.size.height === b.size.height &&
    a.zIndex === b.zIndex &&
    a.opacity === b.opacity &&
    a.visible === b.visible &&
    a.rotation === b.rotation &&
    a.locked === b.locked &&
    JSON.stringify(a.data) === JSON.stringify(b.data)
  );
}

export const CanvasElementRenderer = memo(function CanvasElementRenderer({
  element,
  spaceId,
  isSelected,
  isEditing,
  selectedTool,
  onSelect,
  onDragStart,
  onResizeStart,
  onArrowPointDragStart,
  onDoubleClick,
  onEditEnd,
}: Props) {
  if (!element.visible) return null;

  const isArrow = element.type === 'arrow';
  const isShape = SHAPE_TYPES.has(element.type);
  const isFlowchartNode = FLOWCHART_NODE_TYPES.has(element.type);

  if (isArrow) {
    const bboxX = element.position.x;
    const bboxY = element.position.y;
    const bboxW = Math.max(1, element.size.width);
    const bboxH = Math.max(1, element.size.height);

    return (
      <div
        className={`absolute group ${element.locked ? 'cursor-not-allowed' : 'cursor-move'}`}
        style={{
          left: bboxX,
          top: bboxY,
          width: bboxW,
          height: bboxH,
          zIndex: element.zIndex,
          opacity: element.opacity,
        }}
        onClick={e => {
          e.stopPropagation();
          onSelect(element.id, e.shiftKey);
        }}
        onMouseDown={e => {
          if (!element.locked && (selectedTool === 'select' || selectedTool === 'arrow')) onDragStart(e, element.id);
        }}
      >
        <ArrowSvg
          element={element}
          isSelected={isSelected}
          onPointDragStart={onArrowPointDragStart}
          offsetX={bboxX}
          offsetY={bboxY}
          width={bboxW}
          height={bboxH}
        />
      </div>
    );
  }

  return (
    <div
      className={`absolute group ${element.locked ? 'cursor-not-allowed' : 'cursor-move'}`}
      style={{
        left: element.position.x,
        top: element.position.y,
        width: element.size.width,
        height: element.size.height,
        zIndex: element.zIndex,
        opacity: element.opacity,
        transform: element.rotation ? `rotate(${element.rotation}deg)` : undefined,
      }}
      onClick={e => {
        e.stopPropagation();
        onSelect(element.id, e.shiftKey);
      }}
      onDoubleClick={e => {
        e.stopPropagation();
        onDoubleClick(element.id);
      }}
      onMouseDown={e => {
        if (!element.locked && !isEditing && selectedTool === 'select') onDragStart(e, element.id);
      }}
    >
      {isShape || isFlowchartNode ? (
        <>
          {isShape ? (
            <ShapeSvg
              type={element.type}
              w={element.size.width}
              h={element.size.height}
              data={element.data}
            />
          ) : (
            <FlowchartNodeSvg
              type={element.type}
              w={element.size.width}
              h={element.size.height}
              data={element.data}
            />
          )}
          <div
            className={`absolute inset-0 rounded-lg pointer-events-none transition-shadow ${
              isSelected
                ? 'ring-2 ring-venom-yellow shadow-lg shadow-venom-yellow/20'
                : 'hover:shadow-md'
            }`}
          />
          {isSelected &&
            !element.locked &&
            handlePositions.map(pos => (
              <div
                key={pos}
                data-handle-pos={pos}
                className="absolute w-2 h-2 bg-venom-yellow border border-krait-void rounded-sm z-10"
                style={getHandleStyle(pos, element.size.width, element.size.height)}
                onMouseDown={e => onResizeStart(e, element.id)}
                onClick={e => e.stopPropagation()}
              />
            ))}
        </>
      ) : (
        <>
          <div
            className={`w-full h-full rounded-lg overflow-hidden transition-shadow ${
              isSelected
                ? 'ring-2 ring-venom-yellow shadow-lg shadow-venom-yellow/20'
                : 'shadow-sm hover:shadow-md'
            }`}
            style={{ pointerEvents: 'auto' }}
          >
            {renderContent(element.type, element.data, element.id, spaceId, isEditing, onEditEnd)}
          </div>

          {isSelected &&
            !element.locked &&
            handlePositions.map(pos => (
              <div
                key={pos}
                data-handle-pos={pos}
                className="absolute w-2 h-2 bg-venom-yellow border border-krait-void rounded-sm z-10"
                style={getHandleStyle(pos, element.size.width, element.size.height)}
                onMouseDown={e => onResizeStart(e, element.id)}
                onClick={e => e.stopPropagation()}
              />
            ))}
        </>
      )}
    </div>
  );
}, canvasElementAreEqual);
