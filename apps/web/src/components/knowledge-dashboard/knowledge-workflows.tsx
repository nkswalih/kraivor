'use client';

import { useState } from 'react';
import { Workflow, Play, Loader2, Check, ChevronRight } from 'lucide-react';
import { useWorkflowDefinitions, useRunWorkflow } from '@/lib/hooks/use-knowledge-dashboard';

export function KnowledgeWorkflows({ workspaceId }: { workspaceId: string }) {
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [topic, setTopic] = useState('');
  const [result, setResult] = useState<ReturnType<typeof useRunWorkflow>['data'] | null>(null);

  const definitions = useWorkflowDefinitions();
  const runWorkflow = useRunWorkflow(workspaceId);

  const handleRun = async () => {
    if (!selectedWorkflow) return;
    try {
      const res = await runWorkflow.mutateAsync({
        workflowName: selectedWorkflow,
        topic: topic || undefined,
      });
      setResult(res);
    } catch {
      // error handled by mutation
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {definitions.isLoading ? (
          <>
            <div className="h-24 bg-card border border-border rounded-lg animate-pulse" />
            <div className="h-24 bg-card border border-border rounded-lg animate-pulse" />
          </>
        ) : (
          definitions.data?.map(wf => (
            <button
              key={wf.name}
              onClick={() => setSelectedWorkflow(wf.name)}
              className={`text-left bg-card border rounded-lg p-4 transition-all ${
                selectedWorkflow === wf.name
                  ? 'border-venom-yellow shadow-venom'
                  : 'border-border hover:border-venom-yellow/30'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Workflow className="w-4 h-4 text-venom-yellow" />
                <span className="text-[13px] font-medium text-foreground">{wf.name.replace(/_/g, ' ')}</span>
              </div>
              <p className="text-[11px] text-muted-foreground line-clamp-2">{wf.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] px-1.5 py-0.5 bg-accent rounded">{wf.category}</span>
                <span className="text-[10px] text-muted-foreground">{wf.step_count} steps</span>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Run form */}
      {selectedWorkflow && (
        <div className="bg-card border border-border rounded-lg p-4 mb-6">
          <h3 className="text-[13px] font-medium mb-3">Run: {selectedWorkflow.replace(/_/g, ' ')}</h3>
          <input
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="Topic or query (optional)"
            className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors mb-3"
          />
          <button
            onClick={handleRun}
            disabled={runWorkflow.isPending}
            className="px-4 py-2 bg-venom-yellow text-black text-[12px] font-medium rounded-lg hover:brightness-110 transition-all disabled:opacity-50 flex items-center gap-1.5"
          >
            {runWorkflow.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
            {runWorkflow.isPending ? 'Running...' : 'Run Workflow'}
          </button>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            {result.status === 'completed' ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-yellow-400" />
            )}
            <span className="text-[13px] font-medium">
              {result.workflow_name.replace(/_/g, ' ')} — {result.status}
            </span>
            <span className="text-[11px] text-muted-foreground ml-auto">
              {Math.round(result.total_duration_ms)}ms
            </span>
          </div>
          <div className="space-y-1.5">
            {Object.entries(result.step_results).map(([stepId, sr]) => (
              <div key={stepId} className="flex items-center gap-2 text-[12px]">
                {sr.status === 'completed' ? (
                  <Check className="w-3 h-3 text-green-400" />
                ) : sr.status === 'failed' ? (
                  <span className="w-3 h-3 rounded-full bg-red-400/20" />
                ) : (
                  <span className="w-3 h-3 rounded-full bg-yellow-400/20" />
                )}
                <span className="text-foreground">{stepId}</span>
                <span className="text-muted-foreground">{sr.status}</span>
                <span className="text-muted-foreground ml-auto">{Math.round(sr.duration_ms)}ms</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
