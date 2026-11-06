'use client';

import { useEffect, useRef, useState, useCallback, type ReactNode } from 'react';
import { SlotNavigation, type NavSection } from './slot-navigation';

export const NAV_SECTIONS: NavSection[] = [
  { id: 'overview', label: 'Repository Overview' },
  { id: 'ai-summary', label: 'AI Executive Summary' },
  { id: 'scorecards', label: 'Engineering Scorecards' },
  { id: 'effort', label: 'Estimated Remediation' },
  { id: 'risk', label: 'Business Risk Assessment' },
  { id: 'debt', label: 'Technical Debt Analysis' },
  { id: 'clusters', label: 'Issue Clusters' },
  { id: 'hotspots', label: 'Code Hotspots' },
  { id: 'health', label: 'Service Health Status' },
  { id: 'quick-wins', label: 'Quick Wins' },
  { id: 'scalability', label: 'Scalability Review' },
  { id: 'deployment', label: 'Deployment & Release' },
  { id: 'roadmap', label: 'Sprint Roadmap' },
  { id: 'ownership', label: 'Team Ownership' },
  { id: 'ai-recs', label: 'AI Recommendations' },
];

interface EnterpriseGuideLayoutProps {
  children: ReactNode;
}

function playTick() {
  try {
    const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 1200;
    osc.type = 'sine';
    gain.gain.setValueAtTime(0.02, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.04);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.04);
    ctx.close();
  } catch {}
}

function vibrate() {
  try { navigator.vibrate?.(8); } catch {}
}

export function EnterpriseGuideLayout({ children }: EnterpriseGuideLayoutProps) {
  const [activeSection, setActiveSection] = useState(NAV_SECTIONS[0].id);
  const contentRef = useRef<HTMLDivElement>(null);
  const navRef = useRef<HTMLDivElement>(null);
  const lastTickRef = useRef(0);
  const prevSectionRef = useRef(activeSection);

  useEffect(() => {
    if (prevSectionRef.current === activeSection) return;
    prevSectionRef.current = activeSection;

    const now = Date.now();
    if (now - lastTickRef.current < 80) return;
    lastTickRef.current = now;

    playTick();
    vibrate();
  }, [activeSection]);

  useEffect(() => {
    const container = contentRef.current;
    if (!container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter(e => e.isIntersecting);
        if (visible.length === 0) return;

        const sorted = [...visible].sort(
          (a, b) => a.boundingClientRect.top - b.boundingClientRect.top
        );

        const id = sorted[0].target.getAttribute('data-section');
        if (id) setActiveSection(id);
      },
      {
        root: container,
        rootMargin: '-96px 0px -60% 0px',
        threshold: 0,
      }
    );

    const observe = () => {
      const els = container.querySelectorAll('[data-section]');
      els.forEach(el => observer.observe(el));
    };

    observe();

    const mutationObserver = new MutationObserver(observe);
    mutationObserver.observe(container, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      mutationObserver.disconnect();
    };
  }, []);

  useEffect(() => {
    const navEl = navRef.current;
    const contentEl = contentRef.current;
    if (!navEl || !contentEl) return;

    const wheelHandler = (e: WheelEvent) => {
      e.preventDefault();
      contentEl.scrollBy({ top: e.deltaY, behavior: 'auto' });
    };

    navEl.addEventListener('wheel', wheelHandler, { passive: false });
    return () => navEl.removeEventListener('wheel', wheelHandler, { passive: false } as EventListenerOptions);
  }, []);

  const handleNavigate = useCallback((id: string) => {
    const el = document.querySelector(`[data-section="${id}"]`) as HTMLElement | null;
    const container = contentRef.current;
    if (!el || !container) return;

    const targetTop = el.offsetTop - container.offsetTop;
    const start = container.scrollTop;
    const delta = targetTop - start;
    const duration = 500;
    const startTime = performance.now();

    const ease = (t: number) => 1 - Math.pow(1 - t, 3);

    const frame = (now: number) => {
      const elapsed = now - startTime;
      const t = Math.min(elapsed / duration, 1);
      container.scrollTop = start + delta * ease(t);
      if (t < 1) requestAnimationFrame(frame);
    };

    requestAnimationFrame(frame);
  }, []);

  return (
    <div className="flex flex-1 min-h-0">
      <div ref={navRef} className="relative shrink-0 flex items-center py-8">
        <SlotNavigation
          sections={NAV_SECTIONS}
          activeSection={activeSection}
          onNavigate={handleNavigate}
        />
      </div>
      <div ref={contentRef} className="flex-1 overflow-y-auto">
        {children}
      </div>
    </div>
  );
}
