'use client';

import { cn } from '@/lib/utils';

export interface NavSection {
  id: string;
  label: string;
}

interface SlotNavigationProps {
  sections: NavSection[];
  activeSection: string;
  onNavigate: (id: string) => void;
}

const ITEM_H = 40;
const VISIBLE_ITEMS = 9;
const VISIBLE_HEIGHT = VISIBLE_ITEMS * ITEM_H; // 360px

export function SlotNavigation({ sections, activeSection, onNavigate }: SlotNavigationProps) {
  const activeIndex = sections.findIndex(s => s.id === activeSection);
  const clampedIndex = Math.max(0, Math.min(sections.length - 1, activeIndex < 0 ? 0 : activeIndex));

  const centerOffset = (VISIBLE_ITEMS / 2) * ITEM_H;
  const offset = centerOffset - clampedIndex * ITEM_H;

  const fadeHeight = 24;

  return (
    <nav className="relative flex flex-col items-center justify-center bg-krait-surface1/40 backdrop-blur-sm border-r border-border rounded-r-2xl overflow-hidden"
      style={{ width: 'clamp(200px, 22vw, 260px)', minHeight: `${VISIBLE_HEIGHT + fadeHeight * 2}px` }}
    >
      <div className="absolute top-0 left-0 right-0 z-10 pointer-events-none"
        style={{ height: `${fadeHeight}px`, background: 'linear-gradient(to bottom, hsl(var(--background)) 0%, hsl(var(--background) / 0.5) 50%, transparent 100%)' }}
      />
      <div className="absolute bottom-0 left-0 right-0 z-10 pointer-events-none"
        style={{ height: `${fadeHeight}px`, background: 'linear-gradient(to top, hsl(var(--background)) 0%, hsl(var(--background) / 0.5) 50%, transparent 100%)' }}
      />

      <div
        className="relative w-full overflow-hidden"
        style={{ height: `${VISIBLE_HEIGHT}px` }}
      >
        <div
          className="flex flex-col items-center transition-transform duration-500 will-change-transform"
          style={{
            transform: `translateY(${offset}px)`,
            transitionTimingFunction: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
          }}
        >
          {sections.map((section, idx) => {
            const dist = Math.abs(idx - clampedIndex);
            const isActive = idx === clampedIndex;
            const isAdjacent = dist === 1;
            const opacity = isActive ? 1 : isAdjacent ? 0.6 : dist === 2 ? 0.3 : dist === 3 ? 0.15 : 0;

            return (
              <div key={section.id} className="flex items-center w-full relative"
                style={{ height: `${ITEM_H}px` }}
              >
                <div className="relative shrink-0 h-full"
                  style={{ width: 'clamp(18px, 3vw, 28px)' }}
                >
                  {[8, 16, 20, 24, 32].map(pos => {
                    const isMain = pos === 20;
                    const tickW = isMain
                      ? (isActive ? 14 : isAdjacent ? 10 : dist === 2 ? 7 : dist === 3 ? 5 : 3)
                      : (isActive ? 6 : isAdjacent ? 5 : dist === 2 ? 4 : dist === 3 ? 3 : 2);
                    return (
                      <div
                        key={pos}
                        className="absolute left-0 flex items-center justify-end px-1"
                        style={{ top: `${pos}px`, height: 0, transform: 'translateY(-50%)', width: '100%' }}
                      >
                        <div
                          className={cn(
                            'transition-all duration-300 rounded-full',
                            isMain && isActive ? 'bg-venom-yellow' :
                            isMain ? 'bg-border/30' :
                            isActive ? 'bg-venom-yellow/40' : 'bg-border/15'
                          )}
                          style={{
                            width: `${tickW}px`,
                            height: isMain ? '2px' : '1px',
                            transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
                          }}
                        />
                      </div>
                    );
                  })}
                </div>

                <button
                  onClick={() => onNavigate(section.id)}
                  className={cn(
                    'flex-1 flex items-center justify-center h-full transition-all duration-200 cursor-pointer select-none',
                    isActive ? 'text-venom-yellow' : 'text-text-tertiary'
                  )}
                  style={{
                    opacity,
                    transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
                  }}
                >
                  <span
                    className={cn(
                      'leading-none transition-all duration-200 text-center px-1',
                      isActive ? 'text-sm font-semibold tracking-tight' : 'text-xs font-normal'
                    )}
                  >
                    {section.label}
                  </span>
                </button>

                <div className="relative shrink-0 h-full"
                  style={{ width: 'clamp(18px, 3vw, 28px)' }}
                >
                  {[8, 16, 20, 24, 32].map(pos => {
                    const isMain = pos === 20;
                    const tickW = isMain
                      ? (isActive ? 14 : isAdjacent ? 10 : dist === 2 ? 7 : dist === 3 ? 5 : 3)
                      : (isActive ? 6 : isAdjacent ? 5 : dist === 2 ? 4 : dist === 3 ? 3 : 2);
                    return (
                      <div
                        key={pos}
                        className="absolute right-0 flex items-center justify-start px-1"
                        style={{ top: `${pos}px`, height: 0, transform: 'translateY(-50%)', width: '100%' }}
                      >
                        <div
                          className={cn(
                            'transition-all duration-300 rounded-full',
                            isMain && isActive ? 'bg-venom-yellow' :
                            isMain ? 'bg-border/30' :
                            isActive ? 'bg-venom-yellow/40' : 'bg-border/15'
                          )}
                          style={{
                            width: `${tickW}px`,
                            height: isMain ? '2px' : '1px',
                            transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)',
                          }}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
