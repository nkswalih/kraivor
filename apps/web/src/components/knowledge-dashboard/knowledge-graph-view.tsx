'use client';

import { GitBranch, Loader2 } from 'lucide-react';
import { useKnowledgeGraph, useKnowledgeGraphEntities } from '@/lib/hooks/use-knowledge-dashboard';

export function KnowledgeGraphView({ workspaceId }: { workspaceId: string }) {
  const graph = useKnowledgeGraph(workspaceId);
  const entities = useKnowledgeGraphEntities(workspaceId);

  if (graph.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-muted-foreground animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="bg-card border border-border rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-foreground">{graph.data?.entities ?? 0}</div>
          <div className="text-[11px] text-muted-foreground">Entities</div>
        </div>
        <div className="bg-card border border-border rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-foreground">{graph.data?.entity_types ?? 0}</div>
          <div className="text-[11px] text-muted-foreground">Entity Types</div>
        </div>
        <div className="bg-card border border-border rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-foreground">{graph.data?.relationships ?? 0}</div>
          <div className="text-[11px] text-muted-foreground">Relationships</div>
        </div>
        <div className="bg-card border border-border rounded-lg p-3 text-center">
          <div className="text-xl font-bold text-foreground">{graph.data?.relationship_types ?? 0}</div>
          <div className="text-[11px] text-muted-foreground">Rel. Types</div>
        </div>
      </div>

      {/* Entities */}
      <div className="bg-card border border-border rounded-lg">
        <div className="px-4 py-3 border-b border-border">
          <h3 className="text-[13px] font-medium flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-venom-yellow" />
            Top Entities
          </h3>
        </div>
        <div className="divide-y divide-border">
          {entities.data?.length === 0 ? (
            <div className="p-4 text-[12px] text-muted-foreground">
              No entities found. Start adding knowledge to build your graph.
            </div>
          ) : (
            entities.data?.map((entity, i) => (
              <div key={i} className="px-4 py-3 flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-venom-yellow/10 flex items-center justify-center text-[12px] font-bold text-venom-yellow">
                  {entity.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] font-medium text-foreground">{entity.name}</div>
                  <div className="text-[11px] text-muted-foreground">{entity.type}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-[13px] font-medium text-foreground">{entity.mentions}</div>
                  <div className="text-[11px] text-muted-foreground">mentions</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
