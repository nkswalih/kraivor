'use client';

import { useRef, useState, useEffect } from 'react';

export type ContainerWidth = 'narrow' | 'medium' | 'wide';

export function useContainerWidth(): [React.RefObject<HTMLDivElement | null>, ContainerWidth, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(Infinity);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(entry.contentRect.width);
      }
    });

    ro.observe(el);
    setWidth(el.getBoundingClientRect().width);
    return () => ro.disconnect();
  }, []);

  let label: ContainerWidth = 'narrow';
  if (width >= 400) label = 'wide';
  else if (width >= 300) label = 'medium';

  return [ref, label, width];
}
