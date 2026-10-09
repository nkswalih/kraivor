'use client';

import { useState } from 'react';
import { Ban, CheckCircle2, ChevronDown, ChevronRight, FileCode } from 'lucide-react';
import { cn } from '@/lib/utils';
import { analysisService } from '@/lib/api/analysis-service';
import { SeverityBadge } from './severity-badge';
import { CategoryIcon } from './category-icon';
import type { Finding } from '@/types/domain/analysis';

function FindingRow({ finding, onDismiss }: { finding: Finding; onDismiss: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [dismissing, setDismissing] = useState(false);

  const handleDismiss = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (dismissing) return;
    setDismissing(true);
    try {
      await analysisService.findings.dismiss([finding.id]);
      onDismiss();
    } catch {
      setDismissing(false);
    }
  };

  return (
    <>
      <div
        className={cn(
          'grid grid-cols-[auto_1fr_auto] gap-3 p-3 items-center hover:bg-white/[0.02] transition-colors cursor-pointer text-[13px] group border-b border-border last:border-0',
          finding.status === 'dismissed' && 'opacity-50'
        )}
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => { if (e.key === 'Enter') setExpanded(!expanded); }}
        role="button"
        tabIndex={0}
      >
        <div className="flex items-center gap-2 min-w-0">
          {expanded ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />}
          <SeverityBadge severity={finding.severity} />
          {finding.status === 'dismissed' && (
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
          )}
        </div>
        <div className="min-w-0">
          <p className="text-foreground truncate font-medium">{finding.title}</p>
          <p className="text-muted-foreground text-[12px] truncate mt-0.5">
            {finding.description}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <CategoryIcon category={finding.category} />
          <span className="text-muted-foreground text-[12px] hidden sm:inline">{finding.category}</span>
          {finding.file_path && (
            <span className="text-muted-foreground text-[12px] font-mono hidden md:flex items-center gap-1">
              <FileCode className="w-3 h-3" />
              {finding.file_path}:{finding.line_start}
            </span>
          )}
          {finding.status === 'active' && (
            <button
              onClick={handleDismiss}
              disabled={dismissing}
              className="ml-1 p-1 rounded hover:bg-white/[0.05] text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100"
              title="Dismiss finding"
            >
              <Ban className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
      {expanded && (
        <div className={cn('px-6 pb-3 border-b border-border bg-background/30', finding.status === 'dismissed' && 'opacity-50')}>
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <span className="text-[11px] text-text-tertiary uppercase">Score Impact</span>
              <p className="text-[13px] text-foreground">{finding.score_impact}</p>
            </div>
            <div>
              <span className="text-[11px] text-text-tertiary uppercase">RPM Impact</span>
              <p className="text-[13px] text-foreground">{finding.rpm_impact}</p>
            </div>
          </div>
          <p className="text-[12px] text-text-secondary mb-1">Recommendation</p>
          <p className="text-[13px] text-foreground">{finding.recommendation}</p>
          {finding.enterprise_pattern && (
            <>
              <p className="text-[12px] text-text-secondary mt-3 mb-1">Enterprise Pattern</p>
              <p className="text-[13px] text-foreground">{finding.enterprise_pattern}</p>
            </>
          )}
          {finding.code_snippet && (
            <>
              <p className="text-[12px] text-text-secondary mt-3 mb-1">Code</p>
              <pre className="bg-krait-surface2 border border-border rounded-md p-3 text-[12px] font-mono text-foreground overflow-x-auto">
                {finding.code_snippet}
              </pre>
            </>
          )}
        </div>
      )}
    </>
  );
}

export function FindingsTable({
  findings,
  onDismiss,
  className,
}: {
  findings: Finding[];
  onDismiss?: () => void;
  className?: string;
}) {
  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileCode className="w-8 h-8 text-text-tertiary mb-2" />
        <p className="text-sm text-text-secondary font-medium">No findings</p>
        <p className="text-xs text-text-tertiary mt-1">No issues detected in this category</p>
      </div>
    );
  }

  return (
    <div className={cn('border border-border rounded-lg overflow-hidden', className)}>
      <div className="divide-y divide-border">
        {findings.map((f) => (
          <FindingRow key={f.id} finding={f} onDismiss={onDismiss || (() => {})} />
        ))}
      </div>
    </div>
  );
}
