'use client';

import React, { useRef, useState, useEffect } from 'react';
import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import { PropertiesPanel } from '../panels/properties-panel';
import { LayersPanel } from '../panels/layers-panel';
import { AssetsPanel } from '../panels/assets-panel';
import { Settings2, Layers, Paperclip, BotMessageSquare, ChevronRight } from 'lucide-react';

interface Props {
  spaceId: string;
}

const tabs = [
  { id: 'properties' as const, icon: Settings2, label: 'Properties' },
  { id: 'layers' as const, icon: Layers, label: 'Layers' },
  { id: 'assets' as const, icon: Paperclip, label: 'Assets' },
  { id: 'ai' as const, icon: BotMessageSquare, label: 'AI' },
];

export function CanvasSidebar({ spaceId }: Props) {
  const activePanel = useKnowledgeStore(s => s.activePanel);
  const setActivePanel = useKnowledgeStore(s => s.setActivePanel);
  const sidebarWidth = useKnowledgeStore(s => s.sidebarWidth);
  const showSidebar = useKnowledgeStore(s => s.showSidebar);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showArrow, setShowArrow] = useState(false);

  // Check if tabs overflow and if we can scroll right
  const checkScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;

    const canScrollRight =
      el.scrollWidth > el.clientWidth && el.scrollLeft + el.clientWidth < el.scrollWidth - 8;

    setShowArrow(canScrollRight);
  };

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;

    checkScroll();
    el.addEventListener('scroll', checkScroll);
    window.addEventListener('resize', checkScroll);

    return () => {
      el.removeEventListener('scroll', checkScroll);
      window.removeEventListener('resize', checkScroll);
    };
  }, [sidebarWidth, showSidebar, activePanel]);

  // Fallback observer in case sidebar dynamically changes width without window resize
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;

    const observer = new ResizeObserver(() => checkScroll());
    observer.observe(el);

    return () => observer.disconnect();
  }, []);

  const scrollRight = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: 80, behavior: 'smooth' });
    }
  };

  if (!showSidebar) return null;

  return (
    <div
      className="border-l border-border bg-krait-surface1 flex flex-col shrink-0"
      style={{ width: sidebarWidth }}
    >
      {/* Tab bar */}
      <div className="relative flex items-center border-b border-border h-10 w-full bg-krait-surface1">
        {/* Scrollable track without a scrollbar */}
        <div
          ref={scrollContainerRef}
          className="flex items-center h-full w-full overflow-x-auto no-scrollbar scroll-smooth px-2 gap-1"
        >
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActivePanel(tab.id)}
              className={`flex-none flex items-center justify-center gap-1.5 px-3 h-full text-[11px] font-medium border-b-2 transition-colors ${
                activePanel === tab.id
                  ? 'text-venom-yellow border-venom-yellow bg-venom-yellow/5'
                  : 'text-text-tertiary border-transparent hover:text-foreground hover:bg-krait-surface2'
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              <span className="whitespace-nowrap">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Dynamic Arrow Action Element with Gradient Fade Background */}
        <button
          onClick={scrollRight}
          className={`absolute right-0 top-0 bottom-0 pl-6 pr-2 flex items-center justify-center bg-gradient-to-l from-krait-surface1 via-krait-surface1/90 to-transparent text-text-tertiary hover:text-foreground transition-all duration-300 ${
            showArrow ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
        >
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-y-auto">
        {activePanel === 'properties' && <PropertiesPanel spaceId={spaceId} />}
        {activePanel === 'layers' && <LayersPanel spaceId={spaceId} />}
        {activePanel === 'assets' && <AssetsPanel spaceId={spaceId} />}
        {activePanel === 'ai' && (
          <div className="p-4 text-center text-text-tertiary text-[13px]">
            <BotMessageSquare className="w-8 h-8 mx-auto mb-2 text-venom-yellow" />
            <p>AI assistant coming soon</p>
            <p className="text-[11px] mt-1">Generate diagrams, summaries, and more</p>
          </div>
        )}
      </div>
    </div>
  );
}
