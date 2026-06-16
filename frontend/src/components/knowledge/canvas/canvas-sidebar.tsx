'use client';

import { useKnowledgeStore } from '@/lib/stores/knowledge-store';
import { PropertiesPanel } from '../panels/properties-panel';
import { LayersPanel } from '../panels/layers-panel';
import { AssetsPanel } from '../panels/assets-panel';
import { Settings2, Layers, Paperclip, Sparkles } from 'lucide-react';

interface Props {
  spaceId: string;
}

const tabs = [
  { id: 'properties' as const, icon: Settings2, label: 'Properties' },
  { id: 'layers' as const, icon: Layers, label: 'Layers' },
  { id: 'assets' as const, icon: Paperclip, label: 'Assets' },
  { id: 'ai' as const, icon: Sparkles, label: 'AI' },
];

export function CanvasSidebar({ spaceId }: Props) {
  const activePanel = useKnowledgeStore(s => s.activePanel);
  const setActivePanel = useKnowledgeStore(s => s.setActivePanel);
  const sidebarWidth = useKnowledgeStore(s => s.sidebarWidth);
  const showSidebar = useKnowledgeStore(s => s.showSidebar);

  if (!showSidebar) return null;

  return (
    <div
      className="border-l border-border bg-krait-surface1 flex flex-col shrink-0"
      style={{ width: sidebarWidth }}
    >
      {/* Tab bar */}
      <div className="flex border-b border-border">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActivePanel(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-medium transition-colors ${
              activePanel === tab.id
                ? 'text-venom-yellow border-b-2 border-venom-yellow bg-venom-yellow/5'
                : 'text-text-tertiary hover:text-foreground hover:bg-krait-surface2'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-y-auto">
        {activePanel === 'properties' && <PropertiesPanel spaceId={spaceId} />}
        {activePanel === 'layers' && <LayersPanel spaceId={spaceId} />}
        {activePanel === 'assets' && <AssetsPanel spaceId={spaceId} />}
        {activePanel === 'ai' && (
          <div className="p-4 text-center text-text-tertiary text-[13px]">
            <Sparkles className="w-8 h-8 mx-auto mb-2 text-venom-yellow" />
            <p>AI assistant coming soon</p>
            <p className="text-[11px] mt-1">Generate diagrams, summaries, and more</p>
          </div>
        )}
      </div>
    </div>
  );
}
