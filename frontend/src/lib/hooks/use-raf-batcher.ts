import { useRef, useCallback } from 'react';

export function useRafBatcher<T>() {
  const rafId = useRef(0);
  const pending = useRef<T | null>(null);

  const schedule = useCallback((value: T, commit: (v: T) => void) => {
    pending.current = value;
    if (!rafId.current) {
      rafId.current = requestAnimationFrame(() => {
        rafId.current = 0;
        const v = pending.current;
        pending.current = null;
        if (v !== null) commit(v);
      });
    }
  }, []);

  const flush = useCallback((commit: (v: T) => void) => {
    if (rafId.current) {
      cancelAnimationFrame(rafId.current);
      rafId.current = 0;
    }
    const v = pending.current;
    pending.current = null;
    if (v !== null) commit(v);
  }, []);

  return { schedule, flush };
}
