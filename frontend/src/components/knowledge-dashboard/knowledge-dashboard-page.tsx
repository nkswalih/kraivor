'use client';

import { useState } from 'react';
import {
  Activity,
  Search,
  Upload,
  GitBranch,
  Heart,
  FileText,
  Workflow,
  Package,
} from 'lucide-react';
import { useKnowledgeHealth, useKnowledgeStats, useKnowledgeGraph } from '@/lib/hooks/use-knowledge-dashboard';
import { KnowledgeHealthCard } from './knowledge-health-card';
import { KnowledgeSearchPanel } from './knowledge-search-panel';
import { KnowledgeUploadDialog } from './knowledge-upload-dialog';
import { KnowledgeItemsList } from './knowledge-items-list';
import { KnowledgeGraphView } from './knowledge-graph-view';
import { KnowledgeWorkflows } from './knowledge-workflows';
import { KnowledgeTemplates } from './knowledge-templates';
import { SkeletonCard } from '@/components/ui/skeletons';

type Tab = 'overview' | 'search' | 'graph' | 'workflows' | 'templates';

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'search', label: 'Search', icon: Search },
  { id: 'graph', label: 'Graph', icon: GitBranch },
  { id: 'workflows', label: 'Workflows', icon: Workflow },
  { id: 'templates', label: 'Templates', icon: Package },
];

export function KnowledgeDashboardPage({
  workspaceId,
  workspaceSlug,
}: {
  workspaceId: string;
  workspaceSlug: string;
}) {
  const [tab, setTab] = useState<Tab>('overview');
  const [showUpload, setShowUpload] = useState(false);

  const isOverview = tab === 'overview';

  const health = useKnowledgeHealth(workspaceId, isOverview);
  const stats = useKnowledgeStats(workspaceId);
  const graph = useKnowledgeGraph(workspaceId, isOverview);

  return (
    <div className="flex flex-col h-full animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-venom-yellow/10 flex items-center justify-center">
            <Activity className="w-[18px] h-[18px] text-venom-yellow" />
          </div>
          <div>
            <h1 className="text-lg font-medium">Knowledge Dashboard</h1>
            <p className="text-[12px] text-muted-foreground">
              {stats.data ? `${stats.data.total_items} items across ${stats.data.providers} sources` : 'Loading...'}
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="bg-venom-yellow hover:bg-primary-light text-black text-[12px] font-medium py-1.5 px-3 rounded flex items-center gap-1.5"
        >
          <Upload className="w-3.5 h-3.5" /> Upload
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-6 py-2 border-b border-border shrink-0">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] font-medium transition-colors ${
              tab === t.id
                ? 'bg-venom-yellow/10 text-venom-yellow'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent'
            }`}
          >
            <t.icon className="w-3.5 h-3.5" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {tab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {health.isLoading || stats.isLoading ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : (
              <>
                <KnowledgeHealthCard health={health.data} stats={stats.data} />
                <KnowledgeStatsCard stats={stats.data} />
                <KnowledgeGraphCard graph={graph.data} />
              </>
            )}
            <div className="col-span-full mt-4">
              <KnowledgeItemsList workspaceId={workspaceId} />
            </div>
          </div>
        )}

        {tab === 'search' && <KnowledgeSearchPanel workspaceId={workspaceId} />}
        {tab === 'graph' && <KnowledgeGraphView workspaceId={workspaceId} />}
        {tab === 'workflows' && <KnowledgeWorkflows workspaceId={workspaceId} />}
        {tab === 'templates' && <KnowledgeTemplates workspaceId={workspaceId} />}
      </div>

      {showUpload && (
        <KnowledgeUploadDialog workspaceId={workspaceId} onClose={() => setShowUpload(false)} />
      )}
    </div>
  );
}

function KnowledgeStatsCard({ stats }: { stats: ReturnType<typeof useKnowledgeStats>['data'] }) {
  if (!stats) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-4 h-4 text-venom-yellow" />
        <h3 className="text-[13px] font-medium">Knowledge Base</h3>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-2xl font-bold text-foreground">{stats.total_items}</div>
          <div className="text-[11px] text-muted-foreground">Total Items</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{stats.unique_urls}</div>
          <div className="text-[11px] text-muted-foreground">Unique Sources</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{stats.providers}</div>
          <div className="text-[11px] text-muted-foreground">Providers</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{Math.round(stats.avg_trust * 100)}%</div>
          <div className="text-[11px] text-muted-foreground">Avg Trust</div>
        </div>
      </div>
      {stats.source_types && Object.keys(stats.source_types).length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="text-[11px] text-muted-foreground mb-1.5">By Type</div>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(stats.source_types).map(([type, count]) => (
              <span key={type} className="px-2 py-0.5 bg-accent rounded text-[11px]">
                {type}: {count}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function KnowledgeGraphCard({ graph }: { graph: ReturnType<typeof useKnowledgeGraph>['data'] }) {
  if (!graph) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <GitBranch className="w-4 h-4 text-venom-yellow" />
        <h3 className="text-[13px] font-medium">Knowledge Graph</h3>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-2xl font-bold text-foreground">{graph.entities}</div>
          <div className="text-[11px] text-muted-foreground">Entities</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{graph.relationships}</div>
          <div className="text-[11px] text-muted-foreground">Relationships</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{graph.entity_types}</div>
          <div className="text-[11px] text-muted-foreground">Entity Types</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-foreground">{graph.relationship_types}</div>
          <div className="text-[11px] text-muted-foreground">Rel. Types</div>
        </div>
      </div>
    </div>
  );
}
