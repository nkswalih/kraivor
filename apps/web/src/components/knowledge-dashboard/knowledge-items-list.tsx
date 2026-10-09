'use client';

import { useState } from 'react';
import { FileText, Image, Mic, Globe, Filter } from 'lucide-react';
import { useKnowledgeItems } from '@/lib/hooks/use-knowledge-dashboard';

const SOURCE_ICONS: Record<string, React.ElementType> = {
  pdf: FileText,
  image: Image,
  audio: Mic,
  web: Globe,
  text: FileText,
};

export function KnowledgeItemsList({ workspaceId }: { workspaceId: string }) {
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const items = useKnowledgeItems(workspaceId, 20, 0, filter);

  return (
    <div className="bg-card border border-border rounded-lg">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-[13px] font-medium">Recent Items</h3>
        <div className="flex items-center gap-1">
          <Filter className="w-3.5 h-3.5 text-muted-foreground" />
          {['all', 'pdf', 'image', 'audio', 'web', 'text'].map(type => (
            <button
              key={type}
              onClick={() => setFilter(type === 'all' ? undefined : type)}
              className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                (type === 'all' && !filter) || filter === type
                  ? 'bg-venom-yellow/10 text-venom-yellow'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      <div className="divide-y divide-border">
        {items.isLoading ? (
          <div className="p-4 text-[12px] text-muted-foreground">Loading...</div>
        ) : items.data?.items.length === 0 ? (
          <div className="p-4 text-[12px] text-muted-foreground">No items yet</div>
        ) : (
          items.data?.items.map(item => {
            const Icon = SOURCE_ICONS[item.source_type || 'web'] || Globe;
            return (
              <div key={item.id} className="px-4 py-3 hover:bg-accent/50 transition-colors">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded bg-venom-yellow/10 flex items-center justify-center shrink-0 mt-0.5">
                    <Icon className="w-4 h-4 text-venom-yellow" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px] font-medium text-foreground truncate">
                      {item.title || item.source_url.split('/').pop() || 'Untitled'}
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">
                      {item.content_preview}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] text-muted-foreground">{item.source_provider}</span>
                      {item.language && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-accent rounded">{item.language}</span>
                      )}
                      {item.source_type && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-accent rounded">{item.source_type}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
