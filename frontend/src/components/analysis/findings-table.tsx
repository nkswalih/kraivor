'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, FileCode } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SeverityBadge } from './severity-badge';
import { CategoryIcon } from './category-icon';
import type { Finding } from '@/types/domain/analysis';

function FindingRow({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <div
        className="grid grid-cols-[auto_1fr_auto] gap-3 p-3 items-center hover:bg-white/[0.02] transition-colors cursor-pointer text-[13px] group border-b border-border last:border-0"
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => { if (e.key === 'Enter') setExpanded(!expanded); }}
        role="button"
        tabIndex={0}
      >
        <div className="flex items-center gap-2 min-w-0">
          {expanded ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />}
          <SeverityBadge severity={finding.severity} />
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
        </div>
      </div>
      {expanded && (
        <div className="px-6 pb-3 border-b border-border bg-background/30">
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
  className,
}: {
  findings: Finding[];
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
          <FindingRow key={f.id} finding={f} />
        ))}
      </div>
    </div>
  );
}
