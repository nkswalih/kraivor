'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Search, Loader2, AlertCircle } from 'lucide-react';
import { useFindings } from '@/lib/hooks/use-analysis';
import { FindingsTable } from '@/components/analysis/findings-table';
import { Severity } from '@/types/domain/analysis';
import type { Finding } from '@/types/domain/analysis';

const SEVERITIES = ['', Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW] as const;
const CATEGORIES = ['', 'security', 'performance', 'reliability', 'maintainability', 'devops'] as const;

export default function FindingsPage() {
  const params = useParams<{ workspace: string; jobId: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const jobId = params?.jobId ?? '';

  const [severity, setSeverity] = useState('');
  const [category, setCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useFindings(jobId, {
    severity: severity || undefined,
    category: category || undefined,
    page,
    pageSize: 50,
  });

  const findings = (data?.findings ?? []) as Finding[];
  const total = data?.total ?? 0;

  const filtered = searchQuery
    ? findings.filter(
        (f) =>
          f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          f.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          f.file_path?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : findings;

  return (
    <div className="flex flex-col h-full animate-fade-up">
      <div className="px-6 py-4 border-b border-border shrink-0 bg-background">
        <div className="flex items-center gap-3 mb-3">
          <Link
            href={`/${workspaceSlug}/analysis/jobs/${jobId}`}
            className="p-1.5 border border-border bg-card rounded-md text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-lg font-medium text-foreground">Findings</h1>
          {!isLoading && <span className="text-[12px] text-text-tertiary">({total} total)</span>}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search findings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-[200px] bg-card border border-border text-[12px] text-foreground rounded-md pl-8 pr-3 py-1.5 focus:border-primary focus:outline-none transition-colors"
            />
          </div>

          <select
            value={severity}
            onChange={(e) => { setSeverity(e.target.value); setPage(1); }}
            className="bg-card border border-border text-[12px] text-foreground rounded-md px-2 py-1.5 focus:border-primary focus:outline-none"
          >
            <option value="">All Severities</option>
            {SEVERITIES.filter(Boolean).map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>

          <select
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(1); }}
            className="bg-card border border-border text-[12px] text-foreground rounded-md px-2 py-1.5 focus:border-primary focus:outline-none"
          >
            <option value="">All Categories</option>
            {CATEGORIES.filter(Boolean).map((c) => (
              <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
            ))}
          </select>

          {isLoading && <Loader2 className="w-4 h-4 text-venom-yellow animate-spin" />}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {error ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <AlertCircle className="w-10 h-10 text-color-error mb-3" />
            <p className="text-base font-medium text-text-primary mb-1">Failed to load findings</p>
            <p className="text-sm text-text-tertiary">{error.message}</p>
          </div>
        ) : isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-12 bg-card border border-border rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            <FindingsTable findings={filtered} />
            {total > 50 && (
              <div className="flex items-center justify-between mt-4">
                <span className="text-[12px] text-muted-foreground">{total} total findings</span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page <= 1}
                    className="px-3 py-1 text-[12px] border border-border rounded-md bg-card text-foreground disabled:opacity-30"
                  >
                    Previous
                  </button>
                  <span className="text-[12px] text-muted-foreground px-2">Page {page}</span>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={filtered.length < 50}
                    className="px-3 py-1 text-[12px] border border-border rounded-md bg-card text-foreground disabled:opacity-30"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
