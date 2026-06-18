'use client';

import { useMemo } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';

interface Props {
  spaceId: string;
}

const MINIMAP_SIZE = 180;
const MINIMAP_SCALE = 0.15;

export function CanvasMinimap({ spaceId }: Props) {
  const canvas = useKnowledgeStore(s => s.spaces[spaceId]);
  const setViewport = useKnowledgeStore(s => s.setViewport);
  const showMinimap = useKnowledgeStore(s => s.showMinimap);

  const { viewport, elements } = canvas ?? { viewport: { x: 0, y: 0, zoom: 1 }, elements: [] };

  const bounds = useMemo(() => {
    if (elements.length === 0) return null;
    const xs = elements.map(e => e.position.x);
    const ys = elements.map(e => e.position.y);
    const xMaxs = elements.map(e => e.position.x + e.size.width);
    const yMaxs = elements.map(e => e.position.y + e.size.height);
    return {
      minX: Math.min(...xs) - 100,
      minY: Math.min(...ys) - 100,
      maxX: Math.max(...xMaxs) + 100,
      maxY: Math.max(...yMaxs) + 100,
    };
  }, [elements]);

  if (!showMinimap || !bounds) return null;

  const bw = bounds.maxX - bounds.minX;
  const bh = bounds.maxY - bounds.minY;
  const ratio = Math.min(MINIMAP_SIZE / bw, MINIMAP_SIZE / bh, 1);

  const viewW = (window.innerWidth / viewport.zoom) * ratio;
  const viewH = (window.innerHeight / viewport.zoom) * ratio;
  const viewX = (-viewport.x / viewport.zoom - bounds.minX) * ratio;
  const viewY = (-viewport.y / viewport.zoom - bounds.minY) * ratio;

  return (
    <div className="absolute bottom-4 right-4 z-50 rounded-lg border border-border bg-krait-surface2/90 backdrop-blur-md p-2 shadow-lg select-none">
      <svg
        width={MINIMAP_SIZE}
        height={MINIMAP_SIZE}
        viewBox={`0 0 ${MINIMAP_SIZE} ${MINIMAP_SIZE}`}
        className="rounded"
      >
        <rect width={MINIMAP_SIZE} height={MINIMAP_SIZE} fill="var(--krait-surface-3)" rx="4" />
        {elements.map(el => (
          <rect
            key={el.id}
            x={(el.position.x - bounds.minX) * ratio}
            y={(el.position.y - bounds.minY) * ratio}
            width={el.size.width * ratio}
            height={el.size.height * ratio}
            fill="var(--venom-yellow)"
            opacity={0.4}
            rx={2}
          />
        ))}
        <rect
          x={viewX}
          y={viewY}
          width={viewW}
          height={viewH}
          fill="none"
          stroke="var(--venom-yellow)"
          strokeWidth={1.5}
          rx={2}
        />
      </svg>
    </div>
  );
}
